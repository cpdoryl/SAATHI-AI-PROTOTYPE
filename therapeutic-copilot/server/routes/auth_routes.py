"""Authentication routes — JWT-based login/register for clinicians."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from auth.jwt_handler import create_access_token, verify_password, hash_password
from models import Clinician, Tenant
from loguru import logger

router = APIRouter()


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
    from auth.jwt_handler import decode_token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    new_token = create_access_token(data={
        "sub": payload["sub"],
        "email": payload.get("email"),
        "tenant_id": payload.get("tenant_id"),
    })
    return {"access_token": new_token, "token_type": "bearer"}
