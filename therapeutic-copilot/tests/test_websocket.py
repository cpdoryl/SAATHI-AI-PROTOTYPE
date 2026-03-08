"""
SAATHI AI — WebSocket Unit & Integration Tests

Tests:
  Unit (WebSocketManager):
    1. connect() registers WebSocket in the room dict
    2. disconnect() removes WebSocket from room
    3. broadcast_to_room() delivers message to all connections
    4. send_crisis_alert() emits JSON with type "CRISIS_ALERT"
    5. Broadcast to empty room completes without error
    6. Multiple connections in the same room all receive broadcast

  Integration (FastAPI TestClient):
    7. Clinician WS — accepts connection and echoes acknowledgement
    8. Chat WS — accepts connection and echoes streamed token

All WS-manager unit tests use a lightweight mock WebSocket so no real
network I/O occurs.  Integration tests use FastAPI's synchronous
TestClient which spins up the ASGI app in-process.
"""
import json
import pytest

from services.websocket_manager import WebSocketManager


# ─── Helpers ──────────────────────────────────────────────────────────────────


class _FakeWebSocket:
    """
    Minimal mock that satisfies WebSocketManager's call surface:
      .accept() — coroutine
      .send_text(msg) — coroutine; appends to .sent_messages
    """

    def __init__(self):
        self.accepted: bool = False
        self.sent_messages: list[str] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, message: str) -> None:
        self.sent_messages.append(message)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def manager() -> WebSocketManager:
    """Fresh WebSocketManager instance (no shared state between tests)."""
    return WebSocketManager()


@pytest.fixture
def fake_ws() -> _FakeWebSocket:
    return _FakeWebSocket()


# ─── Unit tests: WebSocketManager ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_registers_websocket_in_room(manager, fake_ws):
    """connect() must add the WebSocket to the named room and call accept()."""
    await manager.connect(fake_ws, room="clinician:clin-001")

    assert fake_ws.accepted is True
    assert "clinician:clin-001" in manager.rooms
    assert fake_ws in manager.rooms["clinician:clin-001"]


@pytest.mark.asyncio
async def test_connect_creates_new_room_for_each_id(manager):
    """Two different room IDs must produce two separate room entries."""
    ws_a = _FakeWebSocket()
    ws_b = _FakeWebSocket()

    await manager.connect(ws_a, room="clinician:clin-001")
    await manager.connect(ws_b, room="clinician:clin-002")

    assert len(manager.rooms) == 2
    assert ws_a in manager.rooms["clinician:clin-001"]
    assert ws_b in manager.rooms["clinician:clin-002"]


@pytest.mark.asyncio
async def test_disconnect_removes_websocket_from_room(manager, fake_ws):
    """disconnect() must remove the WebSocket so the room list is empty."""
    await manager.connect(fake_ws, room="clinician:clin-001")
    assert fake_ws in manager.rooms["clinician:clin-001"]

    manager.disconnect(fake_ws, room="clinician:clin-001")

    assert fake_ws not in manager.rooms["clinician:clin-001"]


@pytest.mark.asyncio
async def test_disconnect_nonexistent_room_does_not_raise(manager, fake_ws):
    """Calling disconnect() for a room that never existed must not raise."""
    # No connect() — room does not exist
    manager.disconnect(fake_ws, room="clinician:ghost-999")


@pytest.mark.asyncio
async def test_broadcast_to_room_delivers_message_to_all_connections(manager):
    """broadcast_to_room() must send the same message to every WS in the room."""
    ws1 = _FakeWebSocket()
    ws2 = _FakeWebSocket()

    await manager.connect(ws1, room="session:sess-abc")
    await manager.connect(ws2, room="session:sess-abc")

    await manager.broadcast_to_room("session:sess-abc", "Hello, tokens!")

    assert ws1.sent_messages == ["Hello, tokens!"]
    assert ws2.sent_messages == ["Hello, tokens!"]


@pytest.mark.asyncio
async def test_broadcast_to_empty_room_completes_without_error(manager):
    """broadcast_to_room() for an empty / unknown room must not raise."""
    # No connections, no explicit room creation
    await manager.broadcast_to_room("session:empty-room", "should be ignored")


@pytest.mark.asyncio
async def test_send_crisis_alert_sends_correct_json_structure(manager, fake_ws):
    """
    send_crisis_alert() must deliver a JSON payload with:
      - "type"  == "CRISIS_ALERT"
      - "data"  containing the exact alert_data dict passed in
    """
    await manager.connect(fake_ws, room="clinician:clin-007")

    alert_data = {
        "patient_id": "pat-123",
        "session_id": "sess-456",
        "severity": 9.5,
        "message": "kill myself",
    }
    await manager.send_crisis_alert(clinician_id="clin-007", alert_data=alert_data)

    assert len(fake_ws.sent_messages) == 1
    payload = json.loads(fake_ws.sent_messages[0])
    assert payload["type"] == "CRISIS_ALERT"
    assert payload["data"] == alert_data


@pytest.mark.asyncio
async def test_send_crisis_alert_broadcasts_to_multiple_clinicians_in_room(manager):
    """
    All WebSockets connected to the same clinician room must each
    receive one CRISIS_ALERT when send_crisis_alert() is called.
    (Handles clinician logged in on two devices simultaneously.)
    """
    ws_device_a = _FakeWebSocket()
    ws_device_b = _FakeWebSocket()

    await manager.connect(ws_device_a, room="clinician:clin-multi")
    await manager.connect(ws_device_b, room="clinician:clin-multi")

    await manager.send_crisis_alert(
        clinician_id="clin-multi",
        alert_data={"session_id": "sess-789", "severity": 8.0},
    )

    for ws in (ws_device_a, ws_device_b):
        assert len(ws.sent_messages) == 1
        payload = json.loads(ws.sent_messages[0])
        assert payload["type"] == "CRISIS_ALERT"
        assert payload["data"]["severity"] == 8.0


@pytest.mark.asyncio
async def test_send_crisis_alert_to_disconnected_clinician_does_not_raise(manager):
    """
    Calling send_crisis_alert() for a clinician with no active WebSocket
    connections must not raise — the alert is silently dropped.
    """
    await manager.send_crisis_alert(
        clinician_id="offline-doc",
        alert_data={"session_id": "sess-000", "severity": 7.5},
    )


# ─── Integration tests: FastAPI endpoints ────────────────────────────────────


@pytest.fixture(scope="module")
def test_client():
    """
    FastAPI TestClient scoped to the module.
    Uses the real app so routes, middleware and the ws_manager singleton
    are all exercised.
    """
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        yield client


def test_clinician_ws_accepts_connection_and_echoes_message(test_client):
    """
    A clinician WebSocket connect to /ws/clinician/{id}:
      - Connection must be accepted (no exception on connect)
      - Sending a text message must result in the same message being
        echoed back (clinician can send acks that broadcast to the room)
    """
    with test_client.websocket_connect("/ws/clinician/clin-001") as ws:
        ws.send_text("ACK:session-start")
        response = ws.receive_text()
        assert response == "ACK:session-start"


def test_chat_ws_accepts_connection_and_echoes_token(test_client):
    """
    A chat WebSocket connected to /ws/chat/{session_id}:
      - Connection must be accepted
      - Sending a token text must result in the same token being echoed
        back (current implementation: broadcast_to_room echoes to sender)
    """
    with test_client.websocket_connect("/ws/chat/sess-abc-123") as ws:
        ws.send_text('{"token": "Hello"}')
        response = ws.receive_text()
        assert response == '{"token": "Hello"}'


def test_two_clinicians_in_different_rooms_do_not_cross_broadcast(test_client):
    """
    Messages sent by clin-001 must not appear in clin-002's room.
    Each clinician must only receive messages broadcast to their own room.
    """
    with test_client.websocket_connect("/ws/clinician/clin-001") as ws1, \
         test_client.websocket_connect("/ws/clinician/clin-002") as ws2:

        ws1.send_text("for-clin-001-only")
        echoed = ws1.receive_text()
        assert echoed == "for-clin-001-only"

        # ws2 must not have received anything; sending its own message confirms isolation
        ws2.send_text("for-clin-002-only")
        echoed2 = ws2.receive_text()
        assert echoed2 == "for-clin-002-only"
