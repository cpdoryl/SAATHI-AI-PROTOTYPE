"""
Appointment booking API — POST (create), GET (list), PUT (cancel).

POST /api/v1/appointments   — save to DB + Razorpay order + Google Calendar event
GET  /api/v1/appointments   — list appointments for the authenticated clinician
PUT  /api/v1/appointments/{id}/cancel — cancel appointment, delete calendar event
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from database import get_db
from models import Appointment, AppointmentStatus, Clinician, Patient
from services.payment_service import PaymentService
from services.calendar_service import CalendarService
from auth.jwt_handler import decode_token

router = APIRouter()
_bearer = HTTPBearer()

_payment_svc = PaymentService()
_calendar_svc = CalendarService()


# ─── Auth helper ──────────────────────────────────────────────────────────────

async def _get_clinician(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
) -> Clinician:
    """Decode JWT and resolve clinician; raises 401/404 on failure."""
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    clinician_id = payload.get("sub")
    result = await db.execute(select(Clinician).where(Clinician.id == clinician_id))
    clinician = result.scalar_one_or_none()
    if not clinician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinician not found")
    return clinician


# ─── Request schemas ──────────────────────────────────────────────────────────

class AppointmentCreateRequest(BaseModel):
    patient_id: str
    scheduled_at: datetime          # ISO 8601, e.g. "2026-03-15T10:00:00+05:30"
    duration_minutes: int = 60
    amount_inr: float               # session fee in ₹
    title: Optional[str] = None     # defaults to "Therapy Session — <patient name>"
    description: Optional[str] = ""


# ─── POST / — Create appointment ──────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: AppointmentCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new appointment:
      1. Validate JWT → resolve clinician
      2. Resolve patient (must belong to same tenant)
      3. Persist Appointment row (status=SCHEDULED, payment_status=pending)
      4. Create Razorpay order → store razorpay_order_id
      5. Create Google Calendar event (if calendar connected) → store google_event_id
      6. Commit and return full appointment details + payment order

    Response:
      { appointment_id, patient_id, clinician_id, scheduled_at, duration_minutes,
        status, payment_status, razorpay_order, google_event_id, meet_link }
    """
    clinician = await _get_clinician(credentials, db)

    # ── 1. Resolve patient ────────────────────────────────────────────────────
    pt_result = await db.execute(select(Patient).where(Patient.id == body.patient_id))
    patient = pt_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if patient.tenant_id != clinician.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient does not belong to your tenant",
        )

    # ── 2. Normalise scheduled_at to IST if naive ─────────────────────────────
    scheduled_at = body.scheduled_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(
            tzinfo=timezone(timedelta(hours=5, minutes=30))
        )
    end_dt = scheduled_at + timedelta(minutes=body.duration_minutes)

    # ── 3. Persist appointment row ────────────────────────────────────────────
    appointment = Appointment(
        patient_id=patient.id,
        clinician_id=clinician.id,
        scheduled_at=scheduled_at,
        duration_minutes=body.duration_minutes,
        amount_inr=body.amount_inr,
        status=AppointmentStatus.SCHEDULED,
        payment_status="pending",
    )
    db.add(appointment)
    await db.flush()  # get appointment.id before calling external services
    logger.info(f"Appointment {appointment.id} flushed to DB for patient {patient.id}")

    # ── 4. Razorpay order ────────────────────────────────────────────────────
    razorpay_order: dict = {}
    try:
        razorpay_order = await _payment_svc.create_order(
            amount_inr=body.amount_inr,
            appointment_id=appointment.id,
        )
        appointment.razorpay_order_id = razorpay_order["order_id"]
        logger.info(
            f"Razorpay order {razorpay_order['order_id']} linked to appointment {appointment.id}"
        )
    except Exception as exc:
        logger.error(f"Razorpay order creation failed for appointment {appointment.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create Razorpay payment order: {str(exc)}",
        )

    # ── 5. Google Calendar event (optional — skip if not connected) ────────────
    google_event_id: Optional[str] = None
    meet_link: Optional[str] = None
    html_link: Optional[str] = None

    if clinician.google_calendar_token:
        summary = body.title or f"Therapy Session — {patient.full_name or 'Patient'}"
        description = body.description or (
            f"Therapy appointment with {clinician.full_name} and patient "
            f"{patient.full_name}. Duration: {body.duration_minutes} min."
        )
        try:
            event_data = await _calendar_svc.create_appointment_event(
                token_json=clinician.google_calendar_token,
                summary=summary,
                start_iso=scheduled_at.isoformat(),
                end_iso=end_dt.isoformat(),
                attendee_email=patient.email or None,
                description=description,
            )
            appointment.google_event_id = event_data["google_event_id"]
            google_event_id = event_data["google_event_id"]
            meet_link = event_data.get("meet_link")
            html_link = event_data.get("html_link")
            logger.info(
                f"Google Calendar event {google_event_id} created for appointment {appointment.id}"
            )
        except Exception as exc:
            # Calendar failure is non-fatal — appointment still created
            logger.warning(
                f"Google Calendar event creation failed for appointment {appointment.id}: {exc}. "
                "Continuing without calendar event."
            )
    else:
        logger.info(
            f"Clinician {clinician.id} has no Google Calendar token — skipping calendar event"
        )

    await db.commit()
    await db.refresh(appointment)
    logger.info(f"Appointment {appointment.id} committed successfully")

    return {
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "clinician_id": appointment.clinician_id,
        "scheduled_at": appointment.scheduled_at.isoformat(),
        "duration_minutes": appointment.duration_minutes,
        "amount_inr": appointment.amount_inr,
        "status": appointment.status,
        "payment_status": appointment.payment_status,
        "razorpay_order": razorpay_order,
        "google_event_id": google_event_id,
        "meet_link": meet_link,
        "calendar_link": html_link,
        "created_at": appointment.created_at.isoformat(),
    }


# ─── GET / — List appointments ────────────────────────────────────────────────

@router.get("/")
async def list_appointments(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    patient_id: Optional[str] = Query(default=None, description="Filter by patient"),
    appt_status: Optional[str] = Query(default=None, alias="status", description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List appointments for the authenticated clinician.
    Optionally filter by patient_id or status.
    Returns paginated results ordered by scheduled_at DESC.
    """
    clinician = await _get_clinician(credentials, db)

    query = (
        select(Appointment)
        .where(Appointment.clinician_id == clinician.id)
        .order_by(Appointment.scheduled_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if patient_id:
        query = query.where(Appointment.patient_id == patient_id)

    if appt_status:
        query = query.where(Appointment.payment_status == appt_status)

    result = await db.execute(query)
    appointments = result.scalars().all()

    logger.info(
        f"Clinician {clinician.id} listed {len(appointments)} appointments "
        f"(patient_id={patient_id}, status={appt_status})"
    )

    return {
        "clinician_id": clinician.id,
        "total": len(appointments),
        "appointments": [
            {
                "appointment_id": a.id,
                "patient_id": a.patient_id,
                "scheduled_at": a.scheduled_at.isoformat(),
                "duration_minutes": a.duration_minutes,
                "amount_inr": a.amount_inr,
                "status": a.status,
                "payment_status": a.payment_status,
                "google_event_id": a.google_event_id,
                "razorpay_order_id": a.razorpay_order_id,
                "created_at": a.created_at.isoformat(),
            }
            for a in appointments
        ],
    }


# ─── PUT /{appointment_id}/cancel ─────────────────────────────────────────────

@router.put("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel an appointment:
      1. Validate JWT → resolve clinician
      2. Find appointment (must belong to this clinician)
      3. Update status → CANCELLED
      4. Delete Google Calendar event if linked
      5. Commit and return confirmation

    Note: Razorpay refund must be initiated separately via POST /api/v1/payments/refund.
    """
    clinician = await _get_clinician(credentials, db)

    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.clinician_id == clinician.id,
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or does not belong to you",
        )

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment is already cancelled",
        )

    # ── Mark cancelled ─────────────────────────────────────────────────────────
    appointment.status = AppointmentStatus.CANCELLED
    logger.info(f"Appointment {appointment_id} marked as CANCELLED by clinician {clinician.id}")

    # ── Delete Google Calendar event if present ────────────────────────────────
    if appointment.google_event_id and clinician.google_calendar_token:
        try:
            await _calendar_svc.delete_event(
                token_json=clinician.google_calendar_token,
                event_id=appointment.google_event_id,
            )
            logger.info(
                f"Google Calendar event {appointment.google_event_id} deleted "
                f"for cancelled appointment {appointment_id}"
            )
        except Exception as exc:
            # Non-fatal — appointment still cancelled in DB
            logger.warning(
                f"Failed to delete calendar event {appointment.google_event_id}: {exc}. "
                "DB record still cancelled."
            )

    await db.commit()

    return {
        "appointment_id": appointment_id,
        "status": "cancelled",
        "message": (
            "Appointment cancelled. Initiate refund via POST /api/v1/payments/refund "
            "if payment was captured."
        ),
    }
