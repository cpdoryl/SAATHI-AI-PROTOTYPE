"""Patients API — list, fetch, and update patients for the clinician dashboard."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from database import get_db
from models import Patient, TherapySession

router = APIRouter()


@router.get("/")
async def list_patients(db: AsyncSession = Depends(get_db)):
    """List all patients. In a multi-tenant setup this would filter by clinician JWT."""
    result = await db.execute(select(Patient).order_by(Patient.created_at.desc()))
    patients = result.scalars().all()
    return {
        "patients": [
            {
                "id": p.id,
                "fullName": p.full_name,
                "email": p.email,
                "phone": p.phone,
                "stage": p.stage.value if p.stage else "lead",
                "dropoutRiskScore": p.dropout_risk_score or 0.0,
                "lastActive": p.last_active.isoformat() if p.last_active else None,
                "clinicianId": p.clinician_id,
                "tenantId": p.tenant_id,
            }
            for p in patients
        ]
    }


@router.get("/{patient_id}")
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Return a single patient's profile."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "id": patient.id,
        "fullName": patient.full_name,
        "email": patient.email,
        "phone": patient.phone,
        "stage": patient.stage.value if patient.stage else "lead",
        "dropoutRiskScore": patient.dropout_risk_score or 0.0,
        "lastActive": patient.last_active.isoformat() if patient.last_active else None,
        "clinicianId": patient.clinician_id,
        "tenantId": patient.tenant_id,
    }


@router.get("/{patient_id}/sessions")
async def list_patient_sessions(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Return all therapy sessions for a patient, ordered by started_at desc."""
    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    if not patient_result.scalar_one_or_none():
        logger.warning(f"Patient not found: {patient_id}")
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await db.execute(
        select(TherapySession)
        .where(TherapySession.patient_id == patient_id)
        .order_by(TherapySession.started_at.desc())
    )
    sessions = result.scalars().all()
    logger.info(f"Patient {patient_id} sessions fetched: {len(sessions)} records")
    return {
        "patient_id": patient_id,
        "sessions": [
            {
                "id": s.id,
                "stage": s.stage,
                "currentStep": s.current_step,
                "status": s.status.value if s.status else "pending",
                "crisisScore": s.crisis_score or 0.0,
                "startedAt": s.started_at.isoformat() if s.started_at else None,
                "endedAt": s.ended_at.isoformat() if s.ended_at else None,
            }
            for s in sessions
        ],
    }
