"""Authentication routes — JWT-based login/register for clinicians."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth.jwt_handler import create_access_token, verify_password

router = APIRouter()


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Authenticate clinician and return JWT access token."""
    # TODO: Query clinician by email, verify password, return token
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register")
async def register(payload: dict, db: AsyncSession = Depends(get_db)):
    """Register a new clinician account under a tenant."""
    return {"message": "Clinician registered", "user_id": "placeholder"}


@router.post("/refresh")
async def refresh_token(token: str, db: AsyncSession = Depends(get_db)):
    """Refresh an expiring JWT token."""
    return {"access_token": "new_token_placeholder", "token_type": "bearer"}
