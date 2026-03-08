"""Payment routes — Razorpay order creation, verification, webhooks."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.payment_service import PaymentService

router = APIRouter()


@router.post("/create-order")
async def create_order(payload: dict, db: AsyncSession = Depends(get_db)):
    """Create a Razorpay order for appointment payment."""
    service = PaymentService()
    order = await service.create_order(
        amount_inr=payload.get("amount_inr"),
        appointment_id=payload.get("appointment_id"),
    )
    return order


@router.post("/verify")
async def verify_payment(payload: dict, db: AsyncSession = Depends(get_db)):
    """Verify Razorpay payment signature post-checkout."""
    service = PaymentService()
    result = await service.verify(
        razorpay_order_id=payload.get("razorpay_order_id"),
        razorpay_payment_id=payload.get("razorpay_payment_id"),
        razorpay_signature=payload.get("razorpay_signature"),
    )
    return result


@router.post("/webhook")
async def handle_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Razorpay server-to-server webhook events."""
    body = await request.body()
    service = PaymentService()
    await service.handle_webhook(body=body, headers=dict(request.headers), db=db)
    return {"status": "ok"}
