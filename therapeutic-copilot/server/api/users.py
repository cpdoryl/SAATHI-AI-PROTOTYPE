"""User (Clinician) management API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

router = APIRouter()


@router.get("/me")
async def get_current_user(db: AsyncSession = Depends(get_db)):
    """Return the authenticated clinician's profile."""
    return {"user": "placeholder"}


@router.put("/me")
async def update_profile(payload: dict, db: AsyncSession = Depends(get_db)):
    """Update clinician profile."""
    return {"message": "Profile updated"}
