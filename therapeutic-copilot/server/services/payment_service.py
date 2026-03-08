"""SAATHI AI — Razorpay Payment Service (India-first)."""
import hmac
import hashlib
import json
from config import settings
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Appointment


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

    def _verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify Razorpay webhook HMAC-SHA256 signature.

        Razorpay signs the raw request body with the webhook secret configured
        in the Razorpay Dashboard. If no webhook secret is configured in env,
        verification is skipped (development mode) with a warning.
        """
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.warning(
                "RAZORPAY_WEBHOOK_SECRET not set — skipping webhook signature verification. "
                "Set this in production for security."
            )
            return True
        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def _update_appointment_payment_status(
        self, db: AsyncSession, order_id: str, new_status: str
    ) -> bool:
        """Find an Appointment by razorpay_order_id and update its payment_status.

        Returns True if the record was found and updated, False otherwise.
        """
        result = await db.execute(
            select(Appointment).where(Appointment.razorpay_order_id == order_id)
        )
        appointment = result.scalar_one_or_none()
        if appointment is None:
            logger.warning(
                f"Razorpay webhook: no Appointment found for order_id={order_id}"
            )
            return False
        appointment.payment_status = new_status
        await db.commit()
        logger.info(
            f"Appointment {appointment.id} payment_status → '{new_status}' "
            f"(order_id={order_id})"
        )
        return True

    async def handle_webhook(self, body: bytes, headers: dict, db: AsyncSession) -> None:
        """Process Razorpay webhook events.

        Supported events:
          - payment.captured  → Appointment.payment_status = "paid"
          - payment.failed    → Appointment.payment_status = "failed"
          - refund.created    → Appointment.payment_status = "refunded"

        Webhook signature is verified via HMAC-SHA256 using
        RAZORPAY_WEBHOOK_SECRET (set in Razorpay Dashboard → Webhooks).
        """
        # ── 1. Verify signature ────────────────────────────────────────────────
        signature = headers.get("x-razorpay-signature", "")
        if not self._verify_webhook_signature(body, signature):
            logger.error("Razorpay webhook: invalid signature — request rejected")
            return

        # ── 2. Parse event ─────────────────────────────────────────────────────
        event = json.loads(body)
        event_type = event.get("event")
        logger.info(f"Razorpay webhook received: event={event_type}")

        # ── 3. Handle payment.captured ─────────────────────────────────────────
        if event_type == "payment.captured":
            payment_entity = event.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            if not order_id:
                logger.error("payment.captured: missing order_id in payload")
                return
            logger.info(f"payment.captured: payment_id={payment_id} order_id={order_id}")
            await self._update_appointment_payment_status(db, order_id, "paid")

        # ── 4. Handle payment.failed ───────────────────────────────────────────
        elif event_type == "payment.failed":
            payment_entity = event.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            if not order_id:
                logger.error("payment.failed: missing order_id in payload")
                return
            error_reason = payment_entity.get("error_reason", "unknown")
            logger.warning(
                f"payment.failed: payment_id={payment_id} order_id={order_id} "
                f"reason={error_reason}"
            )
            await self._update_appointment_payment_status(db, order_id, "failed")

        # ── 5. Handle refund.created ───────────────────────────────────────────
        elif event_type == "refund.created":
            refund_entity = event.get("payload", {}).get("refund", {}).get("entity", {})
            refund_id = refund_entity.get("id")
            payment_id = refund_entity.get("payment_id")
            if not payment_id:
                logger.error("refund.created: missing payment_id in payload")
                return
            logger.info(f"refund.created: refund_id={refund_id} payment_id={payment_id}")
            # Fetch the payment via Razorpay API to resolve order_id
            try:
                client = self._get_client()
                payment_detail = client.payment.fetch(payment_id)
                order_id = payment_detail.get("order_id")
                if not order_id:
                    logger.error(
                        f"refund.created: Razorpay payment {payment_id} has no order_id"
                    )
                    return
                await self._update_appointment_payment_status(db, order_id, "refunded")
            except Exception as exc:
                logger.error(
                    f"refund.created: failed to fetch payment {payment_id} — {exc}"
                )

        else:
            logger.debug(f"Razorpay webhook: unhandled event type '{event_type}' — ignored")
