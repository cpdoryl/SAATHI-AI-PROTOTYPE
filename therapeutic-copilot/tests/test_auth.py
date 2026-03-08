"""
SAATHI AI — Auth Test Suite
Tests authentication endpoints: login, register, token refresh.
Run: cd therapeutic-copilot && pytest tests/test_auth.py -v
"""
import pytest
import asyncio
import sys
import os

# ─── Path & env setup ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_auth.db")
os.environ.setdefault("JWT_SECRET_KEY", "auth-test-secret-key-32-chars-min!")
os.environ.setdefault("DEBUG_MODE", "false")
os.environ.setdefault("TOGETHER_API_KEY", "")
os.environ.setdefault("PINECONE_API_KEY", "")
os.environ.setdefault("RAZORPAY_KEY_ID", "")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "")

# ─── Shared test imports ───────────────────────────────────────────────────────
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
from models import Tenant, Clinician
from auth.jwt_handler import hash_password, decode_token


# ─── In-file test database ─────────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///./test_auth.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

TENANT_ID = "tenant-auth-1"
CLINICIAN_ID = "clinician-auth-1"
CLINICIAN_EMAIL = "auth_test@saathi.ai"
CLINICIAN_PASSWORD = "AuthTest@1234"


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
    """Create tables and seed a tenant + clinician for auth tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as db:
        tenant = Tenant(
            id=TENANT_ID,
            name="Auth Test Clinic",
            domain="auth-test.saathi.ai",
            widget_token="auth-test-widget-token",
            is_active=True,
        )
        db.add(tenant)

        clinician = Clinician(
            id=CLINICIAN_ID,
            tenant_id=TENANT_ID,
            email=CLINICIAN_EMAIL,
            hashed_password=hash_password(CLINICIAN_PASSWORD),
            full_name="Dr. Auth Test",
            is_active=True,
        )
        db.add(clinician)
        await db.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    if os.path.exists("./test_auth.db"):
        os.remove("./test_auth.db")


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Login — correct password → JWT
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_correct_password(client):
    """POST /api/v1/auth/login with correct credentials → 200 + valid JWT."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": CLINICIAN_EMAIL, "password": CLINICIAN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    assert data["token_type"] == "bearer"
    assert data["clinician_id"] == CLINICIAN_ID
    assert data["tenant_id"] == TENANT_ID

    # Verify the JWT decodes correctly with the expected claims
    payload = decode_token(data["access_token"])
    assert payload is not None, "JWT could not be decoded"
    assert payload["sub"] == CLINICIAN_ID
    assert payload["email"] == CLINICIAN_EMAIL


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Login — wrong password → 401
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """POST /api/v1/auth/login with wrong password → 401 Unauthorized."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": CLINICIAN_EMAIL, "password": "WrongPassword!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert "access_token" not in response.json()


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Login — unknown email → 401
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_unknown_email(client):
    """POST /api/v1/auth/login with unregistered email → 401 Unauthorized."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@nowhere.com", "password": CLINICIAN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert "access_token" not in response.json()


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Register → 201
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_new_clinician(client):
    """POST /api/v1/auth/register with valid payload → 201 + clinician_id."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new_clinician@saathi.ai",
            "password": "NewClinician@5678",
            "full_name": "Dr. New Register",
            "tenant_id": TENANT_ID,
        },
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert "clinician_id" in data, "No clinician_id in response"
    assert data["message"] == "Clinician registered"


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client):
    """POST /api/v1/auth/register with already-registered email → 409 Conflict."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": CLINICIAN_EMAIL,
            "password": "AnotherPass@9999",
            "full_name": "Duplicate Clinician",
            "tenant_id": TENANT_ID,
        },
    )
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"


@pytest.mark.asyncio
async def test_register_unknown_tenant_returns_404(client):
    """POST /api/v1/auth/register with unknown tenant_id → 404 Not Found."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "tenant_ghost@saathi.ai",
            "password": "Pass@1234",
            "full_name": "Dr. Ghost",
            "tenant_id": "nonexistent-tenant-id",
        },
    )
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Refresh → new token
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_token_returns_new_jwt(client):
    """POST /api/v1/auth/refresh with valid token → 200 + new access_token."""
    # Step 1: login to get an original token
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": CLINICIAN_EMAIL, "password": CLINICIAN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    original_token = login_response.json()["access_token"]

    # Step 2: refresh using that token (token is a query param per route signature)
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        params={"token": original_token},
    )
    assert refresh_response.status_code == 200, (
        f"Expected 200, got {refresh_response.status_code}: {refresh_response.text}"
    )
    data = refresh_response.json()
    assert "access_token" in data, "No access_token in refresh response"
    assert data["token_type"] == "bearer"

    # New token must decode cleanly and carry the same subject
    new_payload = decode_token(data["access_token"])
    assert new_payload is not None, "Refreshed JWT could not be decoded"
    assert new_payload["sub"] == CLINICIAN_ID
    assert new_payload["email"] == CLINICIAN_EMAIL


@pytest.mark.asyncio
async def test_refresh_token_invalid_returns_401(client):
    """POST /api/v1/auth/refresh with a garbage token → 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        params={"token": "this.is.not.a.valid.jwt"},
    )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
