"""
SAATHI AI — Chat API Integration Tests
"""
import pytest
from httpx import AsyncClient
from main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_start_session(client):
    response = await client.post("/api/v1/chat/start", json={
        "tenant_id": "test-tenant",
        "widget_token": "test-token",
        "language": "en",
    })
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "greeting" in data
    assert data["stage"] in [1, 2, 3]


@pytest.mark.asyncio
async def test_send_message(client):
    """Test that a normal message returns an AI response."""
    response = await client.post("/api/v1/chat/message", json={
        "session_id": "test-session",
        "message": "I have been feeling anxious lately",
        "stage": 2,
    })
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["crisis_score"] < 7.0  # non-crisis message


@pytest.mark.asyncio
async def test_crisis_detection_in_message(client):
    """Test that a crisis message triggers escalation."""
    response = await client.post("/api/v1/chat/message", json={
        "session_id": "test-session",
        "message": "I want to kill myself",
        "stage": 2,
    })
    assert response.status_code == 200
    data = response.json()
    assert data.get("crisis_detected") is True
    assert data.get("escalated") is True
    assert data["crisis_score"] >= 7.0
