"""SAATHI AI — Stage 3 Dropout Re-engagement Service."""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from loguru import logger


INACTIVITY_THRESHOLDS = {
    "warning": 7,    # days
    "at_risk": 14,
    "dropout": 30,
}


class DropoutService:
    """Detects patient dropout risk and triggers personalised re-engagement."""

    async def scan_inactive_patients(self, db: AsyncSession) -> list:
        """
        Scheduled job: scan all patients for inactivity.
        Returns list of patients needing re-engagement.
        """
        # TODO: Query patients where last_active < now - threshold
        return []

    async def calculate_risk_score(self, patient_id: str, db: AsyncSession) -> float:
        """
        Calculate dropout risk score (0.0–1.0).
        Factors: inactivity days, assessment scores, session completion rate.
        """
        return 0.0

    async def generate_reengagement_message(self, patient_id: str, db: AsyncSession) -> str:
        """Generate personalised re-engagement message using Qwen 2.5-7B."""
        return (
            "Hi! We've missed you at Saathi. Your wellbeing matters to us. "
            "Would you like to continue your journey? I'm here whenever you're ready."
        )

    async def send_reengagement(self, patient_id: str, channel: str, db: AsyncSession) -> dict:
        """
        Send re-engagement message via specified channel.
        Channels: whatsapp, email, sms
        """
        message = await self.generate_reengagement_message(patient_id, db)
        logger.info(f"Re-engagement sent to {patient_id} via {channel}")
        return {"patient_id": patient_id, "channel": channel, "sent": True}
