"""Pure payment signature verification (Razorpay + PhonePe).

Security-critical and framework-free so it can be unit-tested with known vectors.
Payment state only advances on a signature that verifies here.
"""
from __future__ import annotations

import base64
import hashlib
import hmac


def _constant_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# ------------------------- Razorpay -------------------------
def razorpay_payment_signature(order_id: str, payment_id: str, secret: str) -> str:
    """HMAC-SHA256 of '<order_id>|<payment_id>' keyed by the API secret."""
    msg = f"{order_id}|{payment_id}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify_razorpay_payment(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    return _constant_eq(razorpay_payment_signature(order_id, payment_id, secret), signature)


def verify_razorpay_webhook(raw_body: bytes, signature_header: str, webhook_secret: str) -> bool:
    """Verify the X-Razorpay-Signature header against the raw request body."""
    expected = hmac.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return _constant_eq(expected, signature_header)


# ------------------------- PhonePe --------------------------
def phonepe_x_verify(base64_payload: str, path: str, salt_key: str, salt_index: int | str) -> str:
    """X-VERIFY = SHA256(base64Payload + path + saltKey) + '###' + saltIndex."""
    digest = hashlib.sha256(f"{base64_payload}{path}{salt_key}".encode()).hexdigest()
    return f"{digest}###{salt_index}"


def verify_phonepe_callback(base64_response: str, x_verify_header: str, salt_key: str, salt_index: int | str) -> bool:
    """Callback X-VERIFY = SHA256(base64Response + saltKey) + '###' + saltIndex."""
    digest = hashlib.sha256(f"{base64_response}{salt_key}".encode()).hexdigest()
    expected = f"{digest}###{salt_index}"
    return _constant_eq(expected, x_verify_header)


def phonepe_encode_request(payload_json: str) -> str:
    """Base64-encode a JSON request body (PhonePe wraps requests as {'request': b64})."""
    return base64.b64encode(payload_json.encode()).decode()
