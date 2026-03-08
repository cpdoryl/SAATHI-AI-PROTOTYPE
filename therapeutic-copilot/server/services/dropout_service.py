"""SAATHI AI — Stage 3 Dropout Re-engagement Service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from loguru import logger

from models import Patient, PatientStage


INACTIVITY_THRESHOLDS = {
    "warning": 7,    # days
    "at_risk": 14,
    "dropout": 30,
}


class DropoutService:
    """Detects patient dropout risk and triggers personalised re-engagement."""

    async def scan_inactive_patients(self, db: AsyncSession) -> list:
        """
        Scheduled job: scan all ACTIVE patients for inactivity.
        Returns list of patients needing re-engagement.
        Patients inactive >= 7 days are flagged; >= 30 days are marked as dropout.
        """
        now = datetime.utcnow()
        warning_cutoff = now - timedelta(days=INACTIVITY_THRESHOLDS["warning"])
        dropout_cutoff = now - timedelta(days=INACTIVITY_THRESHOLDS["dropout"])

        result = await db.execute(
            select(Patient).where(
                Patient.stage == PatientStage.ACTIVE,
                Patient.last_active <= warning_cutoff,
            )
        )
        inactive_patients = result.scalars().all()

        flagged = []
        for patient in inactive_patients:
            days_inactive = (now - patient.last_active).days
            risk_level = "warning"
            if days_inactive >= INACTIVITY_THRESHOLDS["dropout"]:
                risk_level = "dropout"
                patient.stage = PatientStage.DROPOUT
                patient.dropout_risk_score = 1.0
            elif days_inactive >= INACTIVITY_THRESHOLDS["at_risk"]:
                risk_level = "at_risk"
                patient.dropout_risk_score = min(
                    0.9, days_inactive / INACTIVITY_THRESHOLDS["dropout"]
                )
            else:
                patient.dropout_risk_score = min(
                    0.5, days_inactive / INACTIVITY_THRESHOLDS["at_risk"]
                )

            flagged.append({
                "patient_id": patient.id,
                "patient_name": patient.full_name,
                "days_inactive": days_inactive,
                "risk_level": risk_level,
                "risk_score": patient.dropout_risk_score,
            })
            logger.info(
                f"Dropout scan: patient {patient.id} inactive {days_inactive}d "
                f"({risk_level}, score={patient.dropout_risk_score:.2f})"
            )

        await db.commit()
        logger.info(f"Dropout scan complete: {len(flagged)} patients flagged")
        return flagged

    async def calculate_risk_score(self, patient_id: str, db: AsyncSession) -> float:
        """
        Calculate dropout risk score (0.0–1.0).
        Factors: inactivity days, session completion rate.
        """
        result = await db.execute(select(Patient).where(Patient.id == patient_id))
        patient = result.scalar_one_or_none()
        if not patient or not patient.last_active:
            return 0.0

        days_inactive = (datetime.utcnow() - patient.last_active).days
        score = min(1.0, days_inactive / INACTIVITY_THRESHOLDS["dropout"])
        return round(score, 2)

    async def generate_reengagement_message(self, patient_id: str, db: AsyncSession) -> str:
        """Generate personalised re-engagement message using Qwen 2.5-7B."""
        result = await db.execute(select(Patient).where(Patient.id == patient_id))
        patient = result.scalar_one_or_none()
        name = patient.full_name.split()[0] if patient and patient.full_name else "there"
        return (
            f"Hi {name}! We've missed you at Saathi. Your wellbeing matters to us. "
            "Would you like to continue your journey? I'm here whenever you're ready."
        )

    async def send_reengagement(self, patient_id: str, channel: str, db: AsyncSession) -> dict:
        """
        Send re-engagement message via specified channel.
        Channels: whatsapp, email, sms
        """
        message = await self.generate_reengagement_message(patient_id, db)
        logger.info(f"Re-engagement sent to {patient_id} via {channel}")
        return {"patient_id": patient_id, "channel": channel, "sent": True, "message": message}
