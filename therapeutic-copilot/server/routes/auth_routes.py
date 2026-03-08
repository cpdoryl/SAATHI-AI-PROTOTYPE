"""Authentication routes — JWT-based login/register for clinicians."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from auth.jwt_handler import create_access_token, verify_password, hash_password, decode_token
from models import Clinician, Tenant
from config import settings
from loguru import logger

router = APIRouter()
_bearer = HTTPBearer()

BLACKLIST_PREFIX = "blacklist:"


async def _get_redis():
    """Return a connected async Redis client, or None if unavailable."""
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        return client
    except Exception as exc:
        logger.warning(f"Redis unavailable: {exc}")
        return None


async def _is_blacklisted(token: str) -> bool:
    """Return True if the token has been blacklisted (logged out)."""
    client = await _get_redis()
    if client is None:
        return False
    try:
        return await client.exists(f"{BLACKLIST_PREFIX}{token}") == 1
    except Exception as exc:
        logger.warning(f"Redis blacklist check failed: {exc}")
        return False


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Authenticate clinician and return JWT access token."""
    result = await db.execute(
        select(Clinician).where(Clinician.email == form_data.username)
    )
    clinician = result.scalar_one_or_none()

    if not clinician or not verify_password(form_data.password, clinician.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not clinician.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact your clinic administrator.",
        )

    access_token = create_access_token(data={
        "sub": clinician.id,
        "email": clinician.email,
        "tenant_id": clinician.tenant_id,
    })
    logger.info(f"Clinician {clinician.email} authenticated successfully")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "clinician_id": clinician.id,
        "full_name": clinician.full_name,
        "tenant_id": clinician.tenant_id,
    }


@router.post("/register")
async def register(payload: dict, db: AsyncSession = Depends(get_db)):
    """Register a new clinician account under a tenant."""
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == payload.get("tenant_id"))
    )
    if not tenant_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing = await db.execute(
        select(Clinician).where(Clinician.email == payload.get("email"))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    clinician = Clinician(
        tenant_id=payload["tenant_id"],
        email=payload["email"],
        hashed_password=hash_password(payload["password"]),
        full_name=payload.get("full_name", ""),
        specialization=payload.get("specialization"),
    )
    db.add(clinician)
    await db.commit()
    await db.refresh(clinician)
    logger.info(f"Clinician registered: {clinician.email} under tenant {clinician.tenant_id}")
    return {"message": "Clinician registered", "clinician_id": clinician.id}


@router.post("/refresh")
async def refresh_token(token: str, db: AsyncSession = Depends(get_db)):
    """Refresh an expiring JWT token."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    new_token = create_access_token(data={
        "sub": payload["sub"],
        "email": payload.get("email"),
        "tenant_id": payload.get("tenant_id"),
    })
    return {"access_token": new_token, "token_type": "bearer"}


@router.get("/me")
async def get_current_clinician(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated clinician's profile."""
    token = credentials.credentials

    if await _is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clinician_id = payload.get("sub")
    result = await db.execute(
        select(Clinician).where(Clinician.id == clinician_id)
    )
    clinician = result.scalar_one_or_none()

    if not clinician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinician not found")

    if not clinician.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    logger.info(f"GET /me — clinician {clinician.email}")
    return {
        "id": clinician.id,
        "email": clinician.email,
        "full_name": clinician.full_name,
        "tenant_id": clinician.tenant_id,
        "specialization": clinician.specialization,
        "is_active": clinician.is_active,
    }


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """Blacklist the current JWT so it cannot be reused."""
    token = credentials.credentials

    payload = decode_token(token)
    if not payload:
        # Token already invalid — nothing to blacklist, treat as success
        return {"message": "Logged out"}

    # Compute remaining TTL from the token's exp claim
    exp = payload.get("exp")
    if exp:
        remaining_ttl = int(exp - datetime.now(tz=timezone.utc).timestamp())
        if remaining_ttl <= 0:
            # Already expired, nothing to blacklist
            return {"message": "Logged out"}
    else:
        # No exp claim — blacklist for the configured token lifetime
        remaining_ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    client = await _get_redis()
    if client is not None:
        try:
            await client.setex(f"{BLACKLIST_PREFIX}{token}", remaining_ttl, "1")
            logger.info(f"Token blacklisted for clinician {payload.get('email')} (TTL={remaining_ttl}s)")
        except Exception as exc:
            logger.error(f"Redis blacklist write failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Logout service temporarily unavailable. Please try again.",
            )
    else:
        logger.warning("Redis unavailable — logout token not blacklisted")

    return {"message": "Logged out successfully"}
