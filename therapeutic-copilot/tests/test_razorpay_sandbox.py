"""
SAATHI AI — Razorpay Sandbox End-to-End Test
Tests order creation + payment signature verification using mocked Razorpay SDK.
For real sandbox testing, set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to
your Razorpay test-mode keys from dashboard.razorpay.com.
"""
import pytest
import hmac
import hashlib
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_smoke_p0.db")
os.environ.setdefault("JWT_SECRET_KEY", "smoke-test-secret")
# Razorpay sandbox test keys (no real charges, safe to use)
os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_saathi_smoke")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "razorpay_test_secret_smoke")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Order creation (mocked Razorpay SDK)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_razorpay_create_order_success():
    """Create a Razorpay order for ₹500 — verify payload and response structure."""
    from services.payment_service import PaymentService

    mock_order = {
        "id": "order_mock_abc123",
        "entity": "order",
        "amount": 50000,
        "currency": "INR",
        "receipt": "appt_appointment-001",
        "status": "created",
    }

    mock_client = MagicMock()
    mock_client.order.create.return_value = mock_order

    service = PaymentService()
    with patch.object(service, "_get_client", return_value=mock_client):
        result = await service.create_order(amount_inr=500.0, appointment_id="appointment-001")

    assert result["order_id"] == "order_mock_abc123"
    assert result["amount_paise"] == 50000
    assert result["currency"] == "INR"
    assert "key_id" in result

    # Confirm the SDK was called with correct payload
    mock_client.order.create.assert_called_once_with({
        "amount": 50000,
        "currency": "INR",
        "receipt": "appt_appointment-001",
        "notes": {"appointment_id": "appointment-001"},
    })


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Payment signature verification (HMAC-SHA256)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_razorpay_verify_payment_valid_signature():
    """Verify a valid Razorpay HMAC-SHA256 payment signature."""
    from services.payment_service import PaymentService

    key_secret = os.environ["RAZORPAY_KEY_SECRET"]
    order_id = "order_mock_abc123"
    payment_id = "pay_mock_xyz789"

    # Generate a legitimate signature the same way Razorpay does
    body = f"{order_id}|{payment_id}"
    valid_signature = hmac.new(
        key_secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    service = PaymentService()
    result = await service.verify(
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=valid_signature,
    )

    assert result["verified"] is True, f"Signature verification failed: {result}"
    assert result["payment_id"] == payment_id


@pytest.mark.asyncio
async def test_razorpay_verify_payment_invalid_signature():
    """Invalid signature must return verified=False (tampered payment)."""
    from services.payment_service import PaymentService

    service = PaymentService()
    result = await service.verify(
        razorpay_order_id="order_mock_abc123",
        razorpay_payment_id="pay_mock_xyz789",
        razorpay_signature="tampered_signature_that_is_wrong",
    )

    assert result["verified"] is False, "Invalid signature should not verify"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Full e2e flow (order → verify) via HTTP API
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_razorpay_e2e_via_api():
    """End-to-end: POST /create-order → compute signature → POST /verify."""
    from httpx import AsyncClient, ASGITransport
    from main import app

    mock_order = {
        "id": "order_e2e_test_001",
        "entity": "order",
        "amount": 100000,
        "currency": "INR",
        "status": "created",
    }

    import razorpay

    with patch("razorpay.Client") as mock_razorpay_cls:
        mock_client_instance = MagicMock()
        mock_client_instance.order.create.return_value = mock_order
        mock_razorpay_cls.return_value = mock_client_instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Step 1: Create order
            create_resp = await client.post(
                "/api/v1/payments/create-order",
                json={"amount_inr": 1000.0, "appointment_id": "appt-e2e-001"},
            )
            assert create_resp.status_code == 200, f"Create order failed: {create_resp.text}"
            order_data = create_resp.json()
            assert order_data["order_id"] == "order_e2e_test_001"

            # Step 2: Compute valid signature
            key_secret = os.environ["RAZORPAY_KEY_SECRET"]
            order_id = order_data["order_id"]
            payment_id = "pay_e2e_test_001"
            body = f"{order_id}|{payment_id}"
            signature = hmac.new(key_secret.encode(), body.encode(), hashlib.sha256).hexdigest()

            # Step 3: Verify
            verify_resp = await client.post(
                "/api/v1/payments/verify",
                json={
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature,
                },
            )
            assert verify_resp.status_code == 200, f"Verify failed: {verify_resp.text}"
            assert verify_resp.json()["verified"] is True
