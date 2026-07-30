"""Payment signature verification tests (pure crypto)."""
import hashlib
import hmac

from app.features.payments import signatures as S


def test_razorpay_payment_signature_roundtrip():
    secret, oid, pid = "sec", "order_1", "pay_1"
    sig = hmac.new(secret.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    assert S.verify_razorpay_payment(oid, pid, sig, secret)
    assert not S.verify_razorpay_payment(oid, pid, "bad", secret)


def test_razorpay_webhook_rejects_tampered_body():
    body, secret = b'{"e":1}', "whsec"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert S.verify_razorpay_webhook(body, sig, secret)
    assert not S.verify_razorpay_webhook(body + b"x", sig, secret)


def test_phonepe_xverify_and_callback():
    salt, idx = "salt", 1
    b64 = S.phonepe_encode_request('{"a":1}')
    xv = S.phonepe_x_verify(b64, "/pg/v1/pay", salt, idx)
    assert xv.endswith(f"###{idx}") and "###" in xv
    cb = "eyJvayI6dHJ1ZX0="
    good = hashlib.sha256(f"{cb}{salt}".encode()).hexdigest() + f"###{idx}"
    assert S.verify_phonepe_callback(cb, good, salt, idx)
    assert not S.verify_phonepe_callback(cb, "x###1", salt, idx)
