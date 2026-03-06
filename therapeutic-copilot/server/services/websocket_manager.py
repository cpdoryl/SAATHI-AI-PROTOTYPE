"""SAATHI AI — WebSocket Connection Manager for real-time alerts."""
from fastapi import WebSocket
from typing import Dict, List
from loguru import logger


class WebSocketManager:
    """Manages WebSocket connections grouped by room (clinician/session)."""

    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str) -> None:
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)
        logger.info(f"WebSocket connected to room: {room}")

    def disconnect(self, websocket: WebSocket, room: str) -> None:
        if room in self.rooms:
            self.rooms[room].remove(websocket)
        logger.info(f"WebSocket disconnected from room: {room}")

    async def broadcast_to_room(self, room: str, message: str) -> None:
        """Broadcast a message to all connections in a room."""
        for ws in self.rooms.get(room, []):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")

    async def send_crisis_alert(self, clinician_id: str, alert_data: dict) -> None:
        """Send a crisis alert to a specific clinician's dashboard."""
        import json
        room = f"clinician:{clinician_id}"
        await self.broadcast_to_room(room, json.dumps({
            "type": "CRISIS_ALERT",
            "data": alert_data,
        }))
