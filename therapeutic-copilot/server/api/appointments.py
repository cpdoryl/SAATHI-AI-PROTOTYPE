"""Appointment booking API — Google Calendar + Razorpay integration."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

router = APIRouter()


@router.post("/")
async def create_appointment(payload: dict, db: AsyncSession = Depends(get_db)):
    """Create a new appointment (triggers Google Calendar + Razorpay order)."""
    return {"message": "Appointment created", "appointment_id": "placeholder"}


@router.get("/")
async def list_appointments(db: AsyncSession = Depends(get_db)):
    """List appointments for a clinician."""
    return {"appointments": []}


@router.put("/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel an appointment and process refund if applicable."""
    return {"message": f"Appointment {appointment_id} cancelled"}
