"""SAATHI AI — Razorpay Payment Service (India-first)."""
import hmac
import hashlib
from config import settings
from loguru import logger


class PaymentService:
    """Razorpay integration for appointment payment processing."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if not self._client:
            import razorpay
            self._client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        return self._client

    async def create_order(self, amount_inr: float, appointment_id: str) -> dict:
        """Create a Razorpay order (amount in paise)."""
        client = self._get_client()
        amount_paise = int(amount_inr * 100)
        order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"appt_{appointment_id}",
            "notes": {"appointment_id": appointment_id},
        })
        logger.info(f"Razorpay order created: {order['id']} for ₹{amount_inr}")
        return {
            "order_id": order["id"],
            "amount_paise": amount_paise,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
        }

    async def verify(self, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> dict:
        """Verify Razorpay payment signature."""
        body = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()
        verified = hmac.compare_digest(expected, razorpay_signature)
        return {"verified": verified, "payment_id": razorpay_payment_id}

    async def handle_webhook(self, body: bytes, headers: dict) -> None:
        """Process Razorpay webhook events."""
        import json
        event = json.loads(body)
        event_type = event.get("event")
        logger.info(f"Razorpay webhook: {event_type}")
        # TODO: Handle payment.captured, payment.failed, refund.created
