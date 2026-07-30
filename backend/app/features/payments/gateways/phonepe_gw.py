"""PhonePe adapter. Network via httpx; X-VERIFY checks are local + tested."""
from __future__ import annotations

import json

import httpx

from app.core.config import settings
from app.features.payments.gateways.base import IntentResult, PaymentGateway
from app.features.payments.signatures import (
    phonepe_encode_request,
    phonepe_x_verify,
    verify_phonepe_callback,
)

_HOST = "https://api.phonepe.com/apis/hermes"
_PAY_PATH = "/pg/v1/pay"


class PhonePeGateway(PaymentGateway):
    name = "phonepe"

    async def create_intent(self, *, order_number: str, amount: int, currency: str) -> IntentResult:
        payload = {
            "merchantId": settings.phonepe_merchant_id,
            "merchantTransactionId": order_number,
            "amount": amount,
            "paymentInstrument": {"type": "PAY_PAGE"},
        }
        b64 = phonepe_encode_request(json.dumps(payload))
        xverify = phonepe_x_verify(b64, _PAY_PATH, settings.phonepe_salt_key or "", settings.phonepe_salt_index)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_HOST}{_PAY_PATH}",
                headers={"Content-Type": "application/json", "X-VERIFY": xverify},
                json={"request": b64},
            )
            resp.raise_for_status()
            data = resp.json()
        redirect = data.get("data", {}).get("instrumentResponse", {}).get("redirectInfo", {}).get("url")
        return IntentResult(
            provider="phonepe", provider_ref=order_number, amount=amount, currency=currency,
            extra={"redirect_url": redirect},
        )

    def verify_callback(self, data: dict, raw_body: bytes, signature: str) -> bool:
        response_b64 = data.get("response", "")
        return verify_phonepe_callback(
            response_b64, signature, settings.phonepe_salt_key or "", settings.phonepe_salt_index
        )
