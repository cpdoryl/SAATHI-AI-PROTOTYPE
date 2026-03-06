"""SAATHI AI — Stage 1 Lead Management Service."""
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger


class LeadService:
    """Manages lead capture, qualification, and Stage 1 → Stage 2 conversion."""

    async def capture(self, db: AsyncSession, patient_data: dict) -> dict:
        """Create a new lead record from widget conversation."""
        # TODO: Insert Patient record with stage=LEAD
        logger.info(f"Lead captured: {patient_data.get('phone', 'unknown')}")
        return {"lead_id": "placeholder", "stage": "lead"}

    async def qualify(self, db: AsyncSession, lead_id: str, qualification_data: dict) -> dict:
        """Score lead based on conversation depth and booking intent."""
        return {"lead_id": lead_id, "qualified": True, "score": 0.85}

    async def convert_to_patient(self, db: AsyncSession, lead_id: str) -> dict:
        """Promote a lead to active patient (Stage 2)."""
        # TODO: Update Patient.stage = ACTIVE, assign clinician
        return {"lead_id": lead_id, "patient_id": "new_patient_id", "stage": "active"}
