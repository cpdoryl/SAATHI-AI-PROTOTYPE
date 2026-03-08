"""
SAATHI AI — Crisis Detection Service
Real-time NLP crisis scanning with 30+ weighted keywords.
Target response time: <100ms
Severity scale: 0–10 (7+ triggers escalation protocol)
"""
from datetime import datetime
from typing import Dict, List

from loguru import logger
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import Clinician, Patient, SessionStatus, TherapySession
from services.websocket_manager import ws_manager


# Weighted crisis keyword dictionary
# Format: keyword → severity_weight (1–10)
CRISIS_KEYWORDS: Dict[str, float] = {
    # Immediate danger (weight 9-10)
    "kill myself": 10.0,
    "end my life": 10.0,
    "want to die": 9.5,
    "suicide": 9.0,
    "suicidal": 9.0,
    "self harm": 8.5,
    "self-harm": 8.5,
    "cut myself": 8.5,
    "overdose": 9.0,
    "jump off": 8.0,
    "hang myself": 9.5,
    # High risk (weight 6-8)
    "no reason to live": 8.0,
    "don't want to exist": 7.5,
    "better off dead": 8.0,
    "can't go on": 7.0,
    "hopeless": 6.0,
    "worthless": 5.5,
    "burden to everyone": 7.0,
    "nobody cares": 5.0,
    "nothing matters": 6.0,
    # Moderate risk (weight 3-5)
    "can't cope": 5.0,
    "overwhelmed": 4.0,
    "breaking down": 4.5,
    "falling apart": 4.5,
    "giving up": 5.0,
    "exhausted from living": 6.0,
    # Multilingual / Hinglish
    "mar jaana chahta": 9.0,
    "jeena nahi chahta": 9.0,
    "zindagi khatam": 8.5,
}


class CrisisDetectionService:
    """Fast keyword-weighted crisis detection engine."""

    def scan(self, message: str) -> Dict:
        """
        Scan a message for crisis indicators.
        Returns severity score (0–10) and detected keywords.
        """
        message_lower = message.lower()
        detected = []
        max_score = 0.0
        cumulative_score = 0.0

        for keyword, weight in CRISIS_KEYWORDS.items():
            if keyword in message_lower:
                detected.append({"keyword": keyword, "weight": weight})
                max_score = max(max_score, weight)
                cumulative_score += weight * 0.3  # partial accumulation

        # Final score: max keyword weight + scaled cumulative bonus
        severity = min(10.0, max_score + min(2.0, cumulative_score * 0.1))

        return {
            "severity": round(severity, 2),
            "escalate": severity >= 7.0,
            "detected_keywords": detected,
            "message_scanned": True,
        }

    async def escalate(
        self,
        session_id: str,
        patient_id: str,
        severity_score: float,
        db: AsyncSession,
    ) -> Dict:
        """
        Execute crisis escalation protocol:
        1. Log crisis event to DB (update TherapySession status + crisis_score)
        2. Broadcast CRISIS_ALERT to clinician via WebSocket
        3. Send SendGrid email to clinician when severity >= 7
        4. Return emergency resources
        """
        clinician_id: str | None = None
        clinician_email: str | None = None
        clinician_name: str = "Clinician"

        # ── 1. Fetch session and update status in DB ──────────────────────────
        try:
            session_result = await db.execute(
                select(TherapySession).where(TherapySession.id == session_id)
            )
            session = session_result.scalar_one_or_none()
            if session:
                session.status = SessionStatus.CRISIS_ESCALATED
                session.crisis_score = severity_score
                await db.commit()
                logger.warning(
                    f"Crisis escalation logged — session={session_id} "
                    f"patient={patient_id} severity={severity_score}"
                )
        except Exception as exc:
            logger.error(f"DB update failed during crisis escalation: {exc}")

        # ── 2. Resolve clinician details from patient ─────────────────────────
        try:
            patient_result = await db.execute(
                select(Patient).where(Patient.id == patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient and patient.clinician_id:
                clinician_id = patient.clinician_id
                clinician_result = await db.execute(
                    select(Clinician).where(Clinician.id == clinician_id)
                )
                clinician = clinician_result.scalar_one_or_none()
                if clinician:
                    clinician_email = clinician.email
                    clinician_name = clinician.full_name
        except Exception as exc:
            logger.error(f"Clinician lookup failed during crisis escalation: {exc}")

        # ── 3. WebSocket alert to clinician dashboard ─────────────────────────
        if clinician_id:
            try:
                await ws_manager.send_crisis_alert(
                    clinician_id=clinician_id,
                    alert_data={
                        "session_id": session_id,
                        "patient_id": patient_id,
                        "severity": severity_score,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                logger.info(f"Crisis WebSocket alert sent to clinician {clinician_id}")
            except Exception as exc:
                logger.error(f"WebSocket crisis alert failed: {exc}")

        # ── 4. SendGrid email when severity >= 7 ──────────────────────────────
        email_sent = False
        if severity_score >= 7.0 and clinician_email and settings.SENDGRID_API_KEY:
            try:
                subject = f"[SAATHI CRISIS ALERT] Severity {severity_score}/10 — Patient {patient_id}"
                body_html = f"""
                <h2 style="color:#c0392b;">&#9888; Crisis Alert — Immediate Attention Required</h2>
                <p>Dear {clinician_name},</p>
                <p>A crisis indicator has been detected during a therapy session on the SAATHI AI platform.</p>
                <table style="border-collapse:collapse;width:100%;">
                  <tr><td style="padding:6px;font-weight:bold;">Patient ID</td><td style="padding:6px;">{patient_id}</td></tr>
                  <tr><td style="padding:6px;font-weight:bold;">Session ID</td><td style="padding:6px;">{session_id}</td></tr>
                  <tr><td style="padding:6px;font-weight:bold;">Severity Score</td><td style="padding:6px;color:#c0392b;font-weight:bold;">{severity_score} / 10</td></tr>
                  <tr><td style="padding:6px;font-weight:bold;">Detected At (UTC)</td><td style="padding:6px;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                </table>
                <p style="margin-top:16px;">Please log in to the SAATHI dashboard immediately and contact the patient.</p>
                <hr/>
                <p style="font-size:12px;color:#666;">
                  Emergency Helplines (India):<br/>
                  iCall: +91-9152987821 &nbsp;|&nbsp;
                  Vandrevala Foundation: 1860-2662-345 &nbsp;|&nbsp;
                  NIMHANS: 080-46110007
                </p>
                <p style="font-size:11px;color:#999;">This is an automated alert from SAATHI AI — RYL NEUROACADEMY PRIVATE LIMITED.</p>
                """
                message = Mail(
                    from_email=settings.EMAIL_FROM,
                    to_emails=clinician_email,
                    subject=subject,
                    html_content=body_html,
                )
                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                response = sg.send(message)
                email_sent = response.status_code in (200, 202)
                logger.info(
                    f"SendGrid crisis email sent to {clinician_email} "
                    f"— status={response.status_code}"
                )
            except Exception as exc:
                logger.error(f"SendGrid email failed during crisis escalation: {exc}")

        return {
            "escalated": True,
            "session_id": session_id,
            "patient_id": patient_id,
            "severity": severity_score,
            "clinician_notified": clinician_id is not None,
            "email_sent": email_sent,
            "resources": {
                "iCall": "+91-9152987821",
                "Vandrevala Foundation": "1860-2662-345",
                "NIMHANS": "080-46110007",
            },
        }
