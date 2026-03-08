"""Rate limiting middleware using Redis sliding window."""
from fastapi import Request, HTTPException, status
from config import settings
import time

# ─── Rate limit rules ────────────────────────────────────────────────────────
# (path_prefix, max_requests, window_seconds)
RATE_LIMIT_RULES = [
    ("/api/v1/chat", 10, 60),   # 10 req/min for chat (AI-heavy endpoint)
    ("/api/v1/auth", 20, 60),   # 20 req/min for auth (brute-force guard)
    ("", 60, 60),               # 60 req/min default for all other routes
]


def _get_rule(path: str):
    """Return the most-specific rate limit rule for a given path."""
    for prefix, limit, window in RATE_LIMIT_RULES:
        if prefix and path.startswith(prefix):
            return limit, window
    return RATE_LIMIT_RULES[-1][1], RATE_LIMIT_RULES[-1][2]  # default


async def _get_redis():
    """Lazy Redis connection using redis.asyncio."""
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return client
    except Exception:
        return None


async def rate_limit_middleware(request: Request, call_next):
    """
    Sliding window rate limiter backed by Redis sorted sets.

    Algorithm (per IP + per route bucket):
      1. Key: ratelimit:<ip>:<bucket>
      2. ZREMRANGEBYSCORE removes timestamps older than the window
      3. ZCARD counts current requests in the window
      4. If count >= limit → 429 Too Many Requests
      5. ZADD adds the current timestamp; EXPIRE resets TTL
    """
    redis = await _get_redis()
    if redis is None:
        # Redis unavailable — fail open (don't block requests)
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    limit, window = _get_rule(path)

    # Bucket key: combine IP + path prefix for per-route isolation
    bucket = path.split("/")[1:3]  # e.g. ["api", "v1"]
    key = f"ratelimit:{ip}:{'/'.join(bucket)}"

    now = time.time()
    window_start = now - window

    try:
        pipe = redis.pipeline()
        # Remove entries outside the sliding window
        pipe.zremrangebyscore(key, 0, window_start)
        # Count remaining entries
        pipe.zcard(key)
        # Add current request timestamp (score=timestamp, member=timestamp:nano)
        pipe.zadd(key, {f"{now:.6f}": now})
        # Expire the key after the window to avoid orphan keys
        pipe.expire(key, window)
        results = await pipe.execute()
        current_count = results[1]  # zcard result

        await redis.aclose()

        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit} requests per {window}s. Please slow down.",
                headers={"Retry-After": str(window)},
            )
    except HTTPException:
        raise
    except Exception:
        # Redis error — fail open
        pass

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Window"] = str(window)
    return response
