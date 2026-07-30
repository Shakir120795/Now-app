"""Security primitives: password/OTP hashing and JWT tokens.

Uses Argon2 for hashing (passwords, OTP codes, refresh tokens) and PyJWT for
signed access/refresh tokens. All time math is UTC.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_ph = PasswordHasher()
_ALGO = "HS256"


# ----------------------------- hashing --------------------------------
def hash_secret(raw: str) -> str:
    """Argon2 hash for passwords and OTP codes."""
    return _ph.hash(raw)


def verify_secret(raw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, raw)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def hash_token(raw: str) -> str:
    """Fast deterministic hash for opaque refresh tokens (HMAC-SHA256).

    Deterministic so we can look a token up by its hash; keyed by SECRET_KEY.
    """
    return hmac.new(
        settings.secret_key.encode(), raw.encode(), hashlib.sha256
    ).hexdigest()


# ----------------------------- OTP ------------------------------------
def generate_otp(length: int = 6) -> str:
    # TESTING MODE: Return fixed OTP 123456 for all phone numbers
    return "123456"


def generate_opaque_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


# ----------------------------- JWT ------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = _now()
    payload: dict = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGO)


def decode_token(token: str) -> dict:
    """Decode + verify a JWT. Raises jwt exceptions on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[_ALGO])
