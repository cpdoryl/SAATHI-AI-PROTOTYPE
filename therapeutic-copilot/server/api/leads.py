"""Stage 1 — Lead capture & management API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

router = APIRouter()


@router.post("/")
async def capture_lead(payload: dict, db: AsyncSession = Depends(get_db)):
    """Capture a new lead from the widget conversation."""
    return {"message": "Lead captured", "lead_id": "placeholder"}


@router.get("/")
async def list_leads(db: AsyncSession = Depends(get_db)):
    """List all leads for a tenant (clinician dashboard)."""
    return {"leads": []}


@router.put("/{lead_id}/convert")
async def convert_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    """Convert a lead to an active patient (Stage 1 → Stage 2)."""
    return {"message": f"Lead {lead_id} converted to patient"}
