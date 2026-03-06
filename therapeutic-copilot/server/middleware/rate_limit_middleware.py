"""Rate limiting middleware using Redis sliding window."""
from fastapi import Request, HTTPException, status
from config import settings
import time


async def rate_limit_middleware(request: Request, call_next):
    """
    Sliding window rate limiter.
    Limits: 60 req/min per IP for general routes, 10 req/min for /api/v1/chat.
    """
    # TODO: Implement Redis-backed sliding window rate limiting
    response = await call_next(request)
    return response
