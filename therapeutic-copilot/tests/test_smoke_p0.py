"""
SAATHI AI — P0 Smoke Test Suite
Tests all P0 implementations from TASKS.md.
Results are written to RESULTS.md in the repo root.
Run: cd therapeutic-copilot && pytest tests/test_smoke_p0.py -v
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# ─── Path & env setup ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_smoke_p0.db")
os.environ.setdefault("JWT_SECRET_KEY", "smoke-test-secret")
os.environ.setdefault("DEBUG_MODE", "false")
os.environ.setdefault("TOGETHER_API_KEY", "")       # blank → skip real LLM calls
os.environ.setdefault("PINECONE_API_KEY", "")
os.environ.setdefault("RAZORPAY_KEY_ID", "")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "")

# ─── Shared test imports ───────────────────────────────────────────────────────
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from main import app
from database import Base, get_db
from models import Tenant, Clinician, Patient, PatientStage, TherapySession, ChatMessage, SessionStatus
from auth.jwt_handler import hash_password


# ─── In-memory test database ──────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///./test_smoke_p0.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    """Create tables and seed test data once for the whole module."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed a Tenant, Clinician, and Patient
    async with TestSessionLocal() as db:
        tenant = Tenant(
            id="tenant-smoke-1",
            name="Smoke Test Clinic",
            domain="smoke.test",
            widget_token="smoke-widget-token-valid",
            is_active=True,
            pinecone_namespace="smoke",
        )
        db.add(tenant)

        clinician = Clinician(
            id="clinician-smoke-1",
            tenant_id="tenant-smoke-1",
            email="smoke@test.com",
            hashed_password=hash_password("testpass123"),
            full_name="Dr. Smoke Test",
            is_active=True,
        )
        db.add(clinician)

        patient = Patient(
            id="patient-smoke-1",
            tenant_id="tenant-smoke-1",
            clinician_id="clinician-smoke-1",
            full_name="Test Patient",
            stage=PatientStage.ACTIVE,
            last_active=datetime.utcnow(),
        )
        db.add(patient)
        await db.commit()

    yield

    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    if os.path.exists("./test_smoke_p0.db"):
        os.remove("./test_smoke_p0.db")


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Auth /login
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_auth_login(client):
    """Auth /login — POST with valid bcrypt-hashed password, expect JWT returned."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "smoke@test.com", "password": "testpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    assert data["token_type"] == "bearer"
    assert data["clinician_id"] == "clinician-smoke-1"


@pytest.mark.asyncio
async def test_auth_login_wrong_password(client):
    """Auth /login — wrong password must return 401."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "smoke@test.com", "password": "wrongpass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: _detect_patient_stage()
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_detect_patient_stage():
    """_detect_patient_stage() — ACTIVE patient → stage 2."""
    from services.therapeutic_ai_service import TherapeuticAIService

    async with TestSessionLocal() as db:
        service = TherapeuticAIService(db=db)
        stage = await service._detect_patient_stage("patient-smoke-1")
        assert stage == 2, f"Expected stage 2 for ACTIVE patient, got {stage}"


@pytest.mark.asyncio
async def test_detect_patient_stage_unknown():
    """_detect_patient_stage() — unknown patient_id → defaults to stage 1."""
    from services.therapeutic_ai_service import TherapeuticAIService

    async with TestSessionLocal() as db:
        service = TherapeuticAIService(db=db)
        stage = await service._detect_patient_stage("nonexistent-patient-id")
        assert stage == 1, f"Expected stage 1 for unknown patient, got {stage}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: TherapySession persist in start_session()
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_start_session_persists_to_db():
    """start_session() — confirm TherapySession row created in DB."""
    from services.therapeutic_ai_service import TherapeuticAIService

    mock_greeting = "Hello, I'm Saathi. How can I support you today?"

    async with TestSessionLocal() as db:
        service = TherapeuticAIService(db=db)
        with patch.object(service.llm, "generate", new=AsyncMock(return_value=mock_greeting)):
            result = await service.start_session(
                patient_id="patient-smoke-1",
                tenant_id="tenant-smoke-1",
                widget_token="smoke-widget-token-valid",
            )

    assert "session_id" in result, "session_id missing from start_session result"
    session_id = result["session_id"]

    # Confirm DB row
    async with TestSessionLocal() as db:
        row = await db.execute(select(TherapySession).where(TherapySession.id == session_id))
        session = row.scalar_one_or_none()
        assert session is not None, f"TherapySession {session_id} not found in DB"
        assert session.patient_id == "patient-smoke-1"
        assert session.status == SessionStatus.IN_PROGRESS


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: ChatMessage persist in process_message()
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_process_message_persists_chat_messages():
    """process_message() — user + assistant ChatMessage rows saved to DB."""
    from services.therapeutic_ai_service import TherapeuticAIService

    # First create a session
    session_id = None
    async with TestSessionLocal() as db:
        service = TherapeuticAIService(db=db)
        with patch.object(service.llm, "generate", new=AsyncMock(return_value="Hello!")):
            start = await service.start_session(
                patient_id="patient-smoke-1",
                tenant_id="tenant-smoke-1",
                widget_token="smoke-widget-token-valid",
            )
        session_id = start["session_id"]

    # Now send a message
    async with TestSessionLocal() as db:
        service = TherapeuticAIService(db=db)
        with patch.object(service.llm, "generate", new=AsyncMock(return_value="I hear you.")):
            with patch.object(service.rag, "query", new=AsyncMock(return_value=[])):
                await service.process_message(
                    session_id=session_id,
                    message="I have been feeling anxious",
                    stage=2,
                )

    # Verify both messages persisted
    async with TestSessionLocal() as db:
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        messages = result.scalars().all()
        roles = [m.role for m in messages]
        assert "user" in roles, "User ChatMessage not persisted"
        assert "assistant" in roles, "Assistant ChatMessage not persisted"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Stage 2 step advance
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_stage2_step_advance():
    """Stage 2: send two messages, confirm current_step incremented in DB."""
    from services.therapeutic_ai_service import TherapeuticAIService

    session_id = None
    async with TestSessionLocal() as db:
        service = TherapeuticAIService(db=db)
        with patch.object(service.llm, "generate", new=AsyncMock(return_value="Hello!")):
            start = await service.start_session(
                patient_id="patient-smoke-1",
                tenant_id="tenant-smoke-1",
                widget_token="smoke-widget-token-valid",
            )
        session_id = start["session_id"]

    for _ in range(2):
        async with TestSessionLocal() as db:
            service = TherapeuticAIService(db=db)
            with patch.object(service.llm, "generate", new=AsyncMock(return_value="Step response.")):
                with patch.object(service.rag, "query", new=AsyncMock(return_value=[])):
                    await service.process_message(
                        session_id=session_id,
                        message="tell me more",
                        stage=2,
                    )

    async with TestSessionLocal() as db:
        result = await db.execute(select(TherapySession).where(TherapySession.id == session_id))
        session = result.scalar_one_or_none()
        assert session.current_step == 2, f"Expected current_step=2, got {session.current_step}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Crisis WebSocket alert
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_crisis_detection_triggers_alert():
    """Crisis: 'suicide' keyword → crisis_detected=True + WebSocket alert fired."""
    from services.therapeutic_ai_service import TherapeuticAIService
    from services.websocket_manager import ws_manager

    session_id = None
    async with TestSessionLocal() as db:
        service = TherapeuticAIService(db=db)
        with patch.object(service.llm, "generate", new=AsyncMock(return_value="Hello!")):
            start = await service.start_session(
                patient_id="patient-smoke-1",
                tenant_id="tenant-smoke-1",
                widget_token="smoke-widget-token-valid",
            )
        session_id = start["session_id"]

    alert_fired = []

    async def mock_send_crisis_alert(clinician_id, alert_data):
        alert_fired.append({"clinician_id": clinician_id, "data": alert_data})

    with patch.object(ws_manager, "send_crisis_alert", side_effect=mock_send_crisis_alert):
        async with TestSessionLocal() as db:
            service = TherapeuticAIService(db=db)
            result = await service.process_message(
                session_id=session_id,
                message="I want to commit suicide",
                stage=2,
            )

    assert result.get("crisis_detected") is True, "crisis_detected not True"
    assert result.get("escalated") is True, "escalated not True"
    assert result["severity"] >= 7.0, f"severity {result['severity']} below threshold"
    assert len(alert_fired) == 1, "WebSocket alert not fired"
    assert alert_fired[0]["clinician_id"] == "clinician-smoke-1"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Widget token validation
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_widget_token_validation_valid(client):
    """Widget /validate-token — valid token → 200 + valid=True."""
    response = await client.get(
        "/api/v1/widget/validate-token",
        headers={"x-widget-token": "smoke-widget-token-valid"},
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["valid"] is True
    assert data["tenant_id"] == "tenant-smoke-1"


@pytest.mark.asyncio
async def test_widget_token_validation_invalid(client):
    """Widget /validate-token — invalid token → 401."""
    response = await client.get(
        "/api/v1/widget/validate-token",
        headers={"x-widget-token": "bad-token-xyz"},
    )
    assert response.status_code == 401
