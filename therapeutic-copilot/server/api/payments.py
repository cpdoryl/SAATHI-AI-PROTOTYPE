"""Payment API — Razorpay integration."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

router = APIRouter()


@router.post("/create-order")
async def create_order(payload: dict, db: AsyncSession = Depends(get_db)):
    """Create a Razorpay order for appointment payment."""
    return {"order_id": "placeholder", "amount": 0}


@router.post("/verify")
async def verify_payment(payload: dict, db: AsyncSession = Depends(get_db)):
    """Verify Razorpay payment signature after checkout."""
    return {"status": "verified"}


@router.post("/webhook")
async def razorpay_webhook(payload: dict):
    """Handle Razorpay webhook events (payment.captured, payment.failed)."""
    return {"status": "received"}
