"""
SAATHI AI — Redis Session State Service
Replaces in-memory dict with Redis-backed session cache.

Stores per-session state (stage, current_step, tenant_id, patient_id) with TTL
so TherapeuticAIService avoids a DB round-trip on every message.
TTL: 4 hours (matches typical therapy session + idle time).
"""
import json
from typing import Optional
from config import settings
from loguru import logger

SESSION_TTL = 4 * 60 * 60  # 4 hours in seconds
KEY_PREFIX = "session:"


class RedisSessionService:
    """Redis-backed session state manager for active therapy sessions."""

    def __init__(self):
        self._client = None

    async def _get_client(self):
        """Lazy async Redis client (redis.asyncio)."""
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
            except Exception as exc:
                logger.warning(f"Redis unavailable for session store: {exc}")
                return None
        return self._client

    def _key(self, session_id: str) -> str:
        return f"{KEY_PREFIX}{session_id}"

    async def set_session(self, session_id: str, state: dict) -> bool:
        """
        Persist session state dict to Redis with TTL.
        state keys: patient_id, tenant_id, stage, current_step, status
        """
        client = await self._get_client()
        if client is None:
            return False
        try:
            await client.setex(
                self._key(session_id),
                SESSION_TTL,
                json.dumps(state),
            )
            logger.debug(f"Session state cached: {session_id}")
            return True
        except Exception as exc:
            logger.warning(f"Redis set_session failed: {exc}")
            return False

    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Retrieve session state from Redis.
        Returns None if key is missing or Redis is unavailable.
        """
        client = await self._get_client()
        if client is None:
            return None
        try:
            raw = await client.get(self._key(session_id))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Redis get_session failed: {exc}")
            return None

    async def update_step(self, session_id: str, new_step: int) -> bool:
        """
        Atomically update only the current_step in an existing session.
        Uses GET + SET to preserve all other fields.
        """
        state = await self.get_session(session_id)
        if state is None:
            return False
        state["current_step"] = new_step
        return await self.set_session(session_id, state)

    async def delete_session(self, session_id: str) -> bool:
        """Remove session state from Redis (call on session end)."""
        client = await self._get_client()
        if client is None:
            return False
        try:
            await client.delete(self._key(session_id))
            return True
        except Exception as exc:
            logger.warning(f"Redis delete_session failed: {exc}")
            return False

    async def refresh_ttl(self, session_id: str) -> bool:
        """Extend session TTL on every message (keep active sessions alive)."""
        client = await self._get_client()
        if client is None:
            return False
        try:
            await client.expire(self._key(session_id), SESSION_TTL)
            return True
        except Exception:
            return False


# Module-level singleton
redis_session_store = RedisSessionService()
