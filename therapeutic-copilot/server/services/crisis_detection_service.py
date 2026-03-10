"""
SAATHI AI — Crisis Detection Service
======================================
Dual-layer crisis detection: ML model (primary) + keyword safety net.

Detection pipeline:
  1. ML Model (DistilBERT, 6-class, C-SSRS aligned)
     → Phase 1 + Phase 2 combined, 3,500 training examples
     → 100% high-risk recall (safety gate design)
     → Covers: self_harm, passive, active, method, intent, plan/attempt
  2. Keyword Safety Net (30+ weighted phrases, English + Hinglish)
     → Always runs in parallel — belt + suspenders
     → Catches explicit phrases the model might miss due to phrasing
  3. Final score = max(ML severity, keyword severity)
     → Escalate if final score >= 7.0

Response time target: <200ms (ML CPU inference ~40-80ms + keyword scan ~1ms)
Severity scale: 0–10 (7.0+ triggers full escalation protocol)
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import Clinician, Patient, SessionStatus, TherapySession
from services.ml_crisis_service import get_ml_crisis_service
from services.websocket_manager import ws_manager


# ---------------------------------------------------------------------------
# Keyword safety net — catches explicit phrases the model may miss
# Format: phrase → severity weight (0–10 scale)
# ---------------------------------------------------------------------------
CRISIS_KEYWORDS: Dict[str, float] = {
    # Immediate danger (9-10)
    "kill myself": 10.0,
    "end my life": 10.0,
    "want to die": 9.5,
    "suicide": 9.0,
    "suicidal": 9.0,
    "hang myself": 9.5,
    "jump off": 8.0,
    "overdose": 9.0,
    "bought a rope": 9.5,
    "bought pills": 9.0,
    "took all my pills": 9.5,
    # Self-harm (8-9)
    "self harm": 8.5,
    "self-harm": 8.5,
    "cut myself": 8.5,
    "cutting myself": 8.5,
    "burn myself": 8.0,
    # High risk (6-8)
    "no reason to live": 8.0,
    "better off dead": 8.0,
    "don't want to exist": 7.5,
    "burden to everyone": 7.0,
    "can't go on": 7.0,
    "nothing to live for": 7.5,
    "hopeless": 6.0,
    "worthless": 5.5,
    "nobody cares": 5.0,
    "nothing matters": 6.0,
    "giving up": 5.0,
    "exhausted from living": 6.0,
    # Moderate (3-5)
    "can't cope": 5.0,
    "overwhelmed": 4.0,
    "breaking down": 4.5,
    "falling apart": 4.5,
    # Multilingual / Hinglish
    "mar jaana chahta": 9.0,
    "mar jaana chahti": 9.0,
    "jeena nahi chahta": 9.0,
    "jeena nahi chahti": 9.0,
    "zindagi khatam": 8.5,
    "jaan de dunga": 9.5,
    "jaan de dungi": 9.5,
    "khud ko khatam": 9.0,
    # Bengali / Tamil / Hindi variants
    "aatmahatya": 9.0,
    "khud ko hurt": 7.0,
}


# ---------------------------------------------------------------------------
# Keyword scan (synchronous, < 1ms)
# ---------------------------------------------------------------------------

def _keyword_scan(message: str) -> Dict:
    """Fast keyword matching. Returns severity on 0-10 scale."""
    text = message.lower()
    detected = []
    max_score = 0.0
    cumulative = 0.0

    for phrase, weight in CRISIS_KEYWORDS.items():
        if phrase in text:
            detected.append({"keyword": phrase, "weight": weight})
            max_score = max(max_score, weight)
            cumulative += weight * 0.3

    severity = min(10.0, max_score + min(2.0, cumulative * 0.1))
    return {
        "severity": round(severity, 2),
        "detected_keywords": detected,
    }


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class CrisisDetectionService:
    """
    Dual-layer crisis detection: ML model (primary) + keyword safety net.
    Backwards-compatible interface: scan() and escalate() unchanged.
    """

    def scan(self, message: str) -> Dict:
        """
        Scan a message for crisis indicators using both ML model and keywords.

        Returns:
            severity          : float 0-10 (final score — max of ML + keyword)
            escalate          : bool  (True if severity >= 7.0)
            detected_keywords : list  (from keyword safety net)
            ml_crisis_class   : str   (e.g. "intent", "passive")
            ml_confidence     : float (model confidence)
            ml_available      : bool  (True if ML model loaded)
            detection_method  : str   ("ml+keyword" | "keyword_only")
            message_scanned   : bool
        """
        # ── 1. Keyword scan (always runs) ─────────────────────────────────
        kw = _keyword_scan(message)
        kw_severity = kw["severity"]

        # ── 2. ML model scan ──────────────────────────────────────────────
        ml_severity   = 0.0
        ml_class      = "unknown"
        ml_confidence = 0.0
        ml_available  = False

        try:
            svc = get_ml_crisis_service()
            if svc.is_ready:
                ml_result = svc.predict(message)
                if ml_result is not None:
                    ml_severity   = ml_result.severity
                    ml_class      = ml_result.crisis_class
                    ml_confidence = ml_result.confidence
                    ml_available  = True
        except Exception as exc:
            logger.warning(f"ML crisis inference skipped: {exc}")

        # ── 3. Final score: max of both (belt + suspenders) ───────────────
        final_severity = max(ml_severity, kw_severity)

        # ── 4. Keyword match always overrides to escalate if high-weight ──
        # If keyword finds >=7.0 but ML missed, keyword wins (safety net).
        escalate = final_severity >= 7.0

        method = "ml+keyword" if ml_available else "keyword_only"

        logger.debug(
            f"Crisis scan — ML:{ml_severity:.1f}({ml_class}) "
            f"KW:{kw_severity:.1f} → final:{final_severity:.1f} "
            f"escalate:{escalate}"
        )

        return {
            "severity":         round(final_severity, 2),
            "escalate":         escalate,
            "detected_keywords": kw["detected_keywords"],
            "ml_crisis_class":  ml_class,
            "ml_confidence":    ml_confidence,
            "ml_available":     ml_available,
            "detection_method": method,
            "message_scanned":  True,
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
        1. Update TherapySession status + crisis_score in DB
        2. Broadcast CRISIS_ALERT via WebSocket to clinician dashboard
        3. Send SendGrid email when severity >= 7
        4. Return emergency resources

        Interface unchanged — all callers unaffected.
        """
        clinician_id:    Optional[str] = None
        clinician_email: Optional[str] = None
        clinician_name:  str = "Clinician"

        # ── 1. Update session in DB ────────────────────────────────────────
        try:
            result  = await db.execute(
                select(TherapySession).where(TherapySession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                session.status       = SessionStatus.CRISIS_ESCALATED
                session.crisis_score = severity_score
                await db.commit()
                logger.warning(
                    f"Crisis escalation — session={session_id} "
                    f"patient={patient_id} severity={severity_score}"
                )
        except Exception as exc:
            logger.error(f"DB update failed during crisis escalation: {exc}")

        # ── 2. Resolve clinician details ───────────────────────────────────
        try:
            pat_result = await db.execute(
                select(Patient).where(Patient.id == patient_id)
            )
            patient = pat_result.scalar_one_or_none()
            if patient and patient.clinician_id:
                clinician_id = patient.clinician_id
                clin_result  = await db.execute(
                    select(Clinician).where(Clinician.id == clinician_id)
                )
                clinician = clin_result.scalar_one_or_none()
                if clinician:
                    clinician_email = clinician.email
                    clinician_name  = clinician.full_name
        except Exception as exc:
            logger.error(f"Clinician lookup failed during crisis escalation: {exc}")

        # ── 3. WebSocket alert ─────────────────────────────────────────────
        if clinician_id:
            try:
                await ws_manager.send_crisis_alert(
                    clinician_id=clinician_id,
                    alert_data={
                        "session_id": session_id,
                        "patient_id": patient_id,
                        "severity":   severity_score,
                        "timestamp":  datetime.utcnow().isoformat(),
                    },
                )
                logger.info(f"Crisis WebSocket alert sent to clinician {clinician_id}")
            except Exception as exc:
                logger.error(f"WebSocket crisis alert failed: {exc}")

        # ── 4. SendGrid email ──────────────────────────────────────────────
        email_sent = False
        if severity_score >= 7.0 and clinician_email and settings.SENDGRID_API_KEY:
            try:
                subject = (
                    f"[SAATHI CRISIS ALERT] Severity {severity_score}/10 "
                    f"— Patient {patient_id}"
                )
                body_html = f"""
                <h2 style="color:#c0392b;">&#9888; Crisis Alert — Immediate Attention Required</h2>
                <p>Dear {clinician_name},</p>
                <p>A crisis indicator has been detected during a therapy session on the SAATHI AI platform.</p>
                <table style="border-collapse:collapse;width:100%;font-family:sans-serif;">
                  <tr style="background:#fdf2f2;">
                    <td style="padding:8px;font-weight:bold;">Patient ID</td>
                    <td style="padding:8px;">{patient_id}</td>
                  </tr>
                  <tr>
                    <td style="padding:8px;font-weight:bold;">Session ID</td>
                    <td style="padding:8px;">{session_id}</td>
                  </tr>
                  <tr style="background:#fdf2f2;">
                    <td style="padding:8px;font-weight:bold;">Severity Score</td>
                    <td style="padding:8px;color:#c0392b;font-weight:bold;">{severity_score} / 10</td>
                  </tr>
                  <tr>
                    <td style="padding:8px;font-weight:bold;">Detected At (UTC)</td>
                    <td style="padding:8px;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</td>
                  </tr>
                </table>
                <p style="margin-top:16px;font-weight:bold;color:#c0392b;">
                  Please log in to the SAATHI dashboard immediately and contact the patient.
                </p>
                <hr/>
                <p style="font-size:12px;color:#555;">
                  <strong>Emergency Helplines (India):</strong><br/>
                  iCall: +91-9152987821 &nbsp;|&nbsp;
                  Vandrevala Foundation: 1860-2662-345 &nbsp;|&nbsp;
                  NIMHANS: 080-46110007 &nbsp;|&nbsp;
                  AASRA: 9820466627
                </p>
                <p style="font-size:11px;color:#999;">
                  Automated alert from SAATHI AI — RYL NEUROACADEMY PRIVATE LIMITED.
                </p>
                """
                msg = Mail(
                    from_email=settings.EMAIL_FROM,
                    to_emails=clinician_email,
                    subject=subject,
                    html_content=body_html,
                )
                sg       = SendGridAPIClient(settings.SENDGRID_API_KEY)
                response = sg.send(msg)
                email_sent = response.status_code in (200, 202)
                logger.info(
                    f"SendGrid crisis email → {clinician_email} "
                    f"status={response.status_code}"
                )
            except Exception as exc:
                logger.error(f"SendGrid email failed during crisis escalation: {exc}")

        return {
            "escalated":           True,
            "session_id":          session_id,
            "patient_id":          patient_id,
            "severity":            severity_score,
            "clinician_notified":  clinician_id is not None,
            "email_sent":          email_sent,
            "resources": {
                "iCall":               "+91-9152987821",
                "Vandrevala Foundation": "1860-2662-345",
                "NIMHANS":             "080-46110007",
                "AASRA":               "9820466627",
            },
        }
