"""Razorpay adapter. Network calls use httpx; signature checks are local + tested."""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.features.payments.gateways.base import IntentResult, PaymentGateway
from app.features.payments.signatures import (
    verify_razorpay_payment,
    verify_razorpay_webhook,
)

_API = "https://api.razorpay.com/v1"


class RazorpayGateway(PaymentGateway):
    name = "razorpay"

    async def create_intent(self, *, order_number: str, amount: int, currency: str) -> IntentResult:
        auth = (settings.razorpay_key_id or "", settings.razorpay_key_secret or "")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_API}/orders",
                auth=auth,
                json={"amount": amount, "currency": currency, "receipt": order_number,
                      "payment_capture": 1},
            )
            resp.raise_for_status()
            data = resp.json()
        return IntentResult(
            provider="razorpay", provider_ref=data["id"], amount=amount, currency=currency,
            extra={"key_id": settings.razorpay_key_id, "razorpay_order_id": data["id"]},
        )

    def verify_callback(self, data: dict, raw_body: bytes, signature: str) -> bool:
        # Client verify: {razorpay_order_id, razorpay_payment_id, razorpay_signature}
        if data.get("razorpay_payment_id"):
            return verify_razorpay_payment(
                data["razorpay_order_id"], data["razorpay_payment_id"],
                data.get("razorpay_signature", ""), settings.razorpay_key_secret or "",
            )
        # Webhook: raw-body HMAC
        return verify_razorpay_webhook(raw_body, signature, settings.razorpay_webhook_secret or "")
