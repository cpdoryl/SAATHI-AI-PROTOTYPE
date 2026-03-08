"""
SAATHI AI — Demo Database Seeder
Seeds: 1 tenant, 1 clinician, 3 patients (LEAD/ACTIVE/DROPOUT),
       1 therapy session (5 messages), 1 PHQ-9 assessment.

Run from the server directory:
  cd therapeutic-copilot/server
  python scripts/setup_db.py
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Ensure server/ is on path so imports resolve (database, models, config)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, engine, Base
from models import (
    Tenant, Clinician, Patient, TherapySession, ChatMessage, Assessment,
    PatientStage, SessionStatus,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Seed Data Constants ──────────────────────────────────────────────────────

TENANT_ID = "demo-tenant-001"
CLINICIAN_ID = "demo-clinician-001"
PATIENT_LEAD_ID = "demo-patient-lead-001"
PATIENT_ACTIVE_ID = "demo-patient-active-001"
PATIENT_DROPOUT_ID = "demo-patient-dropout-001"
SESSION_ID = "demo-session-001"
ASSESSMENT_ID = "demo-assessment-001"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return pwd_context.hash(password)


async def _exists(session: AsyncSession, model, pk: str) -> bool:
    result = await session.get(model, pk)
    return result is not None


# ─── Seeders ──────────────────────────────────────────────────────────────────

async def seed_tenant(session: AsyncSession) -> None:
    if await _exists(session, Tenant, TENANT_ID):
        logger.info("Tenant already exists — skipping")
        return
    tenant = Tenant(
        id=TENANT_ID,
        name="Demo Clinic",
        domain="demo.saathiai.com",
        widget_token="demo-token-123",
        plan="professional",
        is_active=True,
        pinecone_namespace="demo-clinic",
        created_at=datetime.utcnow(),
    )
    session.add(tenant)
    logger.success("Created tenant: Demo Clinic (widget_token=demo-token-123)")


async def seed_clinician(session: AsyncSession) -> None:
    if await _exists(session, Clinician, CLINICIAN_ID):
        logger.info("Clinician already exists — skipping")
        return
    clinician = Clinician(
        id=CLINICIAN_ID,
        tenant_id=TENANT_ID,
        email="admin@demo.com",
        hashed_password=_hash("Demo@1234"),
        full_name="Dr. Demo Admin",
        specialization="Clinical Psychology",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    session.add(clinician)
    logger.success("Created clinician: admin@demo.com / Demo@1234")


async def seed_patients(session: AsyncSession) -> None:
    patients = [
        Patient(
            id=PATIENT_LEAD_ID,
            tenant_id=TENANT_ID,
            clinician_id=CLINICIAN_ID,
            full_name="Arjun Mehta",
            phone="+91-9000000001",
            email="arjun.mehta@example.com",
            stage=PatientStage.LEAD,
            language="en",
            cultural_context="urban_india",
            dropout_risk_score=0.15,
            last_active=datetime.utcnow() - timedelta(days=3),
            created_at=datetime.utcnow() - timedelta(days=10),
        ),
        Patient(
            id=PATIENT_ACTIVE_ID,
            tenant_id=TENANT_ID,
            clinician_id=CLINICIAN_ID,
            full_name="Priya Sharma",
            phone="+91-9000000002",
            email="priya.sharma@example.com",
            stage=PatientStage.ACTIVE,
            language="hi",
            cultural_context="urban_india",
            dropout_risk_score=0.08,
            last_active=datetime.utcnow() - timedelta(hours=6),
            created_at=datetime.utcnow() - timedelta(days=45),
        ),
        Patient(
            id=PATIENT_DROPOUT_ID,
            tenant_id=TENANT_ID,
            clinician_id=CLINICIAN_ID,
            full_name="Rahul Verma",
            phone="+91-9000000003",
            email="rahul.verma@example.com",
            stage=PatientStage.DROPOUT,
            language="en",
            cultural_context="urban_india",
            dropout_risk_score=0.82,
            last_active=datetime.utcnow() - timedelta(days=30),
            created_at=datetime.utcnow() - timedelta(days=90),
        ),
    ]
    for p in patients:
        if await _exists(session, Patient, p.id):
            logger.info(f"Patient {p.full_name} already exists — skipping")
            continue
        session.add(p)
        logger.success(f"Created patient: {p.full_name} ({p.stage.value})")


async def seed_session_with_messages(session: AsyncSession) -> None:
    if await _exists(session, TherapySession, SESSION_ID):
        logger.info("Demo session already exists — skipping")
        return

    therapy_session = TherapySession(
        id=SESSION_ID,
        patient_id=PATIENT_ACTIVE_ID,
        stage=1,
        current_step=3,
        status=SessionStatus.COMPLETED,
        crisis_score=0.05,
        session_summary=(
            "Patient reported mild anxiety around workplace stress. "
            "Engaged well with Stage 1 rapport-building. No crisis indicators. "
            "Recommended breathing exercises."
        ),
        ai_insights={
            "dominant_emotion": "anxiety",
            "stage_recommendation": 1,
            "keywords_flagged": [],
            "next_step": "Continue Stage 1 — explore coping strategies",
        },
        started_at=datetime.utcnow() - timedelta(hours=2),
        ended_at=datetime.utcnow() - timedelta(hours=1),
    )
    session.add(therapy_session)

    messages = [
        ChatMessage(
            id=f"demo-msg-00{i + 1}",
            session_id=SESSION_ID,
            role=role,
            content=content,
            crisis_keywords_detected=[],
            created_at=datetime.utcnow() - timedelta(hours=2) + timedelta(minutes=i * 10),
        )
        for i, (role, content) in enumerate([
            ("user",      "Namaste, I've been feeling really stressed at work lately."),
            ("assistant", "Namaste Priya ji. I hear you — workplace stress can feel overwhelming. Can you tell me more about what's been happening?"),
            ("user",      "My manager keeps piling on tasks and I feel like I can never catch up. It's affecting my sleep too."),
            ("assistant", "That sounds exhausting. Sleep disruption often makes everything feel harder to manage. On a scale of 1 to 10, how would you rate your stress this week?"),
            ("user",      "Maybe a 7. Some days are okay but most days feel heavy."),
        ])
    ]
    for msg in messages:
        session.add(msg)

    logger.success(f"Created demo session with {len(messages)} messages for Priya Sharma")


async def seed_phq9_assessment(session: AsyncSession) -> None:
    if await _exists(session, Assessment, ASSESSMENT_ID):
        logger.info("PHQ-9 assessment already exists — skipping")
        return

    # PHQ-9: 9 items scored 0-3; scores map to severity
    # 0-4 None, 5-9 Mild, 10-14 Moderate, 15-19 Moderately Severe, 20-27 Severe
    phq9_responses = {
        "q1_little_interest":       1,   # Several days
        "q2_feeling_down":          1,   # Several days
        "q3_sleep_problems":        2,   # More than half the days
        "q4_tired":                 1,   # Several days
        "q5_appetite_changes":      0,   # Not at all
        "q6_feeling_bad_about_self": 1,  # Several days
        "q7_concentration":         1,   # Several days
        "q8_moving_or_speaking":    0,   # Not at all
        "q9_better_off_dead":       0,   # Not at all
    }
    total_score = sum(phq9_responses.values())  # 7

    assessment = Assessment(
        id=ASSESSMENT_ID,
        patient_id=PATIENT_ACTIVE_ID,
        assessment_type="PHQ-9",
        responses=phq9_responses,
        score=float(total_score),
        severity="Mild",
        administered_at=datetime.utcnow() - timedelta(days=7),
    )
    session.add(assessment)
    logger.success(f"Created PHQ-9 assessment for Priya Sharma (score={total_score}, severity=Mild)")


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    logger.info("SAATHI AI — Database Seeder Starting")
    logger.info("Creating tables if they do not exist (dev/SQLite only)...")

    # In production use Alembic; here we create_all for local dev convenience
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await seed_tenant(session)
            await seed_clinician(session)
            await seed_patients(session)
            await seed_session_with_messages(session)
            await seed_phq9_assessment(session)

    logger.success("─────────────────────────────────────────────")
    logger.success("Demo seed complete. Login credentials:")
    logger.success("  Email    : admin@demo.com")
    logger.success("  Password : Demo@1234")
    logger.success("  Widget   : demo-token-123")
    logger.success("─────────────────────────────────────────────")


if __name__ == "__main__":
    asyncio.run(main())
