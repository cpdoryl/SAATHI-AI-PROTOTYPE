"""
SAATHI AI — Stage 1 Lead Management Service
============================================
Manages lead scoring, qualification, and Stage 1 → Stage 2 conversion.

Called from therapeutic_ai_service.py after each Stage 1 LLM response to:
  1. Update Patient.last_active timestamp
  2. Store running lead score (mapped to dropout_risk_score as inverse proxy
     until a dedicated lead_score column is added in a migration)
  3. Detect booking intent and promote LEAD → ACTIVE when confirmed

Booking intent threshold: lead_score >= 0.75 AND booking_intent_detected=True
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from models import Patient, PatientStage


# Score threshold above which a LEAD is promoted to ACTIVE
BOOKING_CONVERSION_THRESHOLD = 0.75


class LeadService:
    """Manages lead capture, qualification, and Stage 1 → Stage 2 conversion."""

    async def update_lead_score(
        self,
        db: AsyncSession,
        patient_id: str,
        lead_score: float,
        booking_intent_detected: bool,
        lead_factors: dict,
    ) -> dict:
        """
        Persist the latest lead score for a patient and promote to ACTIVE
        if booking threshold is met.

        Args:
            db:                      Async DB session (from caller — NOT committed here)
            patient_id:              Patient UUID
            lead_score:              0.0-1.0 score from Stage 1 LoRA service
            booking_intent_detected: True when LLM detected booking intent
            lead_factors:            Factor dict from Stage 1 service (for logging)

        Returns:
            dict with promoted flag and new stage
        """
        result = await db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            logger.warning(f"[LeadService] Patient {patient_id} not found")
            return {"promoted": False, "stage": "unknown"}

        # Touch last_active on every Stage 1 turn
        patient.last_active = datetime.utcnow()

        # Use dropout_risk_score field as inverse lead proxy (0=high risk, 1=engaged)
        # TODO: add lead_score column in next DB migration and use that directly
        patient.dropout_risk_score = round(1.0 - lead_score, 4)

        promoted = False
        if (
            patient.stage == PatientStage.LEAD
            and booking_intent_detected
            and lead_score >= BOOKING_CONVERSION_THRESHOLD
        ):
            patient.stage = PatientStage.ACTIVE
            promoted = True
            logger.info(
                f"[LeadService] Patient {patient_id} promoted LEAD -> ACTIVE "
                f"(score={lead_score:.2f}, factors={list(lead_factors.keys())})"
            )

        # Caller is responsible for db.commit()
        return {
            "promoted": promoted,
            "stage": patient.stage.value,
            "lead_score": lead_score,
        }

    async def capture(self, db: AsyncSession, patient_data: dict) -> dict:
        """Create a new lead record from widget conversation."""
        logger.info(f"Lead captured: {patient_data.get('phone', 'unknown')}")
        return {"lead_id": "placeholder", "stage": "lead"}

    async def qualify(
        self, db: AsyncSession, lead_id: str, qualification_data: dict
    ) -> dict:
        """Return qualification status based on lead score."""
        score = qualification_data.get("lead_score", 0.0)
        return {
            "lead_id": lead_id,
            "qualified": score >= 0.50,
            "score": score,
        }

    async def convert_to_patient(self, db: AsyncSession, lead_id: str) -> dict:
        """Manually promote a lead to active patient (Stage 2)."""
        result = await db.execute(
            select(Patient).where(Patient.id == lead_id)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            return {"error": "Patient not found"}
        patient.stage = PatientStage.ACTIVE
        logger.info(f"[LeadService] Manual conversion: {lead_id} -> ACTIVE")
        return {"lead_id": lead_id, "patient_id": lead_id, "stage": "active"}
