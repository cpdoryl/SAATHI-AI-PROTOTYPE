"""
Google Calendar OAuth routes.

Endpoints:
  GET  /api/v1/calendar/auth-url       — return OAuth URL as JSON (JWT auth)
  GET  /api/v1/calendar/callback       — exchange code, store token in DB
  POST /api/v1/calendar/events         — create a Google Calendar event + Meet link
  GET  /api/v1/calendar/events         — list upcoming events for authenticated clinician
  GET  /api/v1/calendar/authorize      — legacy: browser redirect to Google consent page
  GET  /api/v1/calendar/oauth/callback — legacy alias for /callback
  GET  /api/v1/calendar/status         — check if clinician has connected calendar
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import get_db
from models import Clinician, Patient
from services.calendar_service import CalendarService
from auth.jwt_handler import decode_token
from loguru import logger

router = APIRouter()
_bearer = HTTPBearer()


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_clinician_from_jwt(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
) -> Clinician:
    """Decode JWT, resolve clinician from DB, raise 401/404 on failure."""
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


# ─── Request / Response schemas ───────────────────────────────────────────────

class CreateEventRequest(BaseModel):
    clinician_id: str
    patient_id: str
    scheduled_at: datetime          # ISO 8601, e.g. "2026-03-10T10:00:00+05:30"
    duration_minutes: int = 60
    title: Optional[str] = None     # defaults to "Therapy Session"
    description: Optional[str] = ""


# ─── GET /auth-url ─────────────────────────────────────────────────────────────

@router.get("/auth-url")
async def get_auth_url(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the Google OAuth authorization URL as JSON.
    The clinician_id from the JWT is embedded as the OAuth state parameter
    so /callback knows which DB row to update.

    Response: { "auth_url": "https://accounts.google.com/o/oauth2/auth?..." }
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    clinician = await _get_clinician_from_jwt(credentials, db)
    service = CalendarService()
    auth_url = service.get_authorization_url(state=clinician.id)

    logger.info(f"Auth URL generated for clinician {clinician.id}")
    return {"auth_url": auth_url}


# ─── GET /callback ─────────────────────────────────────────────────────────────

@router.get("/callback")
async def google_oauth_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Google OAuth callback — exchanges authorization code for tokens and persists
    the token JSON on the Clinician.google_calendar_token column.

    The 'state' param carries the clinician_id set by /auth-url or /authorize.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'code' or 'state' query parameter",
        )

    result = await db.execute(select(Clinician).where(Clinician.id == state))
    clinician = result.scalar_one_or_none()
    if not clinician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinician not found")

    service = CalendarService()
    try:
        token_json = service.exchange_code_for_token(code)
    except Exception as exc:
        logger.error(f"Google token exchange failed for clinician {state}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange OAuth authorization code with Google",
        )

    clinician.google_calendar_token = token_json
    await db.commit()
    logger.info(f"Google Calendar token stored for clinician {state}")

    return {
        "message": "Google Calendar connected successfully",
        "clinician_id": state,
    }


# ─── POST /events ──────────────────────────────────────────────────────────────

@router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    body: CreateEventRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Google Calendar event for a therapy appointment.

    Looks up the clinician's stored OAuth token and creates an event that
    includes a Google Meet conferencing link.

    Input:
      { clinician_id, patient_id, scheduled_at, duration_minutes, title?, description? }

    Output:
      { event_id, html_link, meet_link, start, end }
    """
    # Resolve clinician
    cl_result = await db.execute(select(Clinician).where(Clinician.id == body.clinician_id))
    clinician = cl_result.scalar_one_or_none()
    if not clinician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinician not found")

    if not clinician.google_calendar_token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Clinician has not connected Google Calendar. Call GET /api/v1/calendar/auth-url first.",
        )

    # Resolve patient for attendee email
    pt_result = await db.execute(select(Patient).where(Patient.id == body.patient_id))
    patient = pt_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Build ISO 8601 start/end strings
    start_dt = body.scheduled_at
    if start_dt.tzinfo is None:
        # Treat naive datetimes as IST (UTC+5:30)
        start_dt = start_dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    end_dt = start_dt + timedelta(minutes=body.duration_minutes)

    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()

    summary = body.title or f"Therapy Session — {patient.full_name or 'Patient'}"
    description = body.description or (
        f"Therapy appointment with {clinician.full_name} and patient {patient.full_name}."
    )

    service = CalendarService()
    try:
        event_data = await service.create_appointment_event(
            token_json=clinician.google_calendar_token,
            summary=summary,
            start_iso=start_iso,
            end_iso=end_iso,
            attendee_email=patient.email or None,
            description=description,
        )
    except Exception as exc:
        logger.error(f"Google Calendar event creation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create Google Calendar event: {str(exc)}",
        )

    logger.info(
        f"Calendar event {event_data['google_event_id']} created for "
        f"clinician {body.clinician_id} / patient {body.patient_id}"
    )
    return {
        "event_id": event_data["google_event_id"],
        "html_link": event_data["html_link"],
        "meet_link": event_data["meet_link"],
        "start": start_iso,
        "end": end_iso,
    }


# ─── GET /events ───────────────────────────────────────────────────────────────

@router.get("/events")
async def list_calendar_events(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    max_results: int = Query(default=20, ge=1, le=100),
    time_min: Optional[str] = Query(default=None, description="ISO 8601 lower bound (default: now)"),
    db: AsyncSession = Depends(get_db),
):
    """
    List upcoming Google Calendar events for the authenticated clinician.

    Response: [ { event_id, summary, start, end, meet_link, html_link, status } ]
    """
    clinician = await _get_clinician_from_jwt(credentials, db)

    if not clinician.google_calendar_token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Clinician has not connected Google Calendar. Call GET /api/v1/calendar/auth-url first.",
        )

    service = CalendarService()
    try:
        events = await service.list_events(
            token_json=clinician.google_calendar_token,
            max_results=max_results,
            time_min=time_min,
        )
    except Exception as exc:
        logger.error(f"Google Calendar list events failed for clinician {clinician.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to retrieve calendar events: {str(exc)}",
        )

    return {"clinician_id": clinician.id, "events": events}


# ─── Legacy: GET /authorize — browser redirect ─────────────────────────────────

@router.get("/authorize")
async def authorize_google_calendar(clinician_id: str = Query(...)):
    """
    Start the Google OAuth flow for a clinician (browser redirect variant).
    Prefer GET /auth-url for API/SPA clients; this endpoint suits direct browser links.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    service = CalendarService()
    auth_url = service.get_authorization_url(state=clinician_id)
    return RedirectResponse(url=auth_url)


# ─── Legacy alias: GET /oauth/callback ────────────────────────────────────────

@router.get("/oauth/callback")
async def google_oauth_callback_legacy(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Legacy callback path — delegates to /callback handler."""
    return await google_oauth_callback(code=code, state=state, error=error, db=db)


# ─── GET /status ───────────────────────────────────────────────────────────────

@router.get("/status")
async def calendar_status(
    clinician_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Check whether a clinician has connected their Google Calendar."""
    result = await db.execute(select(Clinician).where(Clinician.id == clinician_id))
    clinician = result.scalar_one_or_none()
    if not clinician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinician not found")
    return {
        "clinician_id": clinician_id,
        "calendar_connected": bool(clinician.google_calendar_token),
    }
