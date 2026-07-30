"""Shared helpers for integration tests (require the DB engine)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.security import hash_secret


async def seed_otp(engine, phone: str, code: str = "123456") -> None:
    """Insert a ready-to-verify OTP row for `phone`."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO otp_requests (phone, code_hash, purpose, expires_at)
                VALUES (:p, :h, 'login', :exp)
                """
            ),
            {"p": phone, "h": hash_secret(code), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        )


async def grant_super_admin(engine, user_id: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO user_roles (user_id, role_id)
                SELECT :uid, id FROM roles WHERE name = 'super_admin'
                ON CONFLICT DO NOTHING
                """
            ),
            {"uid": user_id},
        )


async def login(client, engine, phone: str) -> dict:
    """Full OTP login → returns {access_token, refresh_token, user}."""
    await client.post("/auth/otp/request", json={"phone": phone})
    await seed_otp(engine, phone)
    r = await client.post("/auth/otp/verify", json={"phone": phone, "code": "123456"})
    assert r.status_code == 200, r.text
    return r.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
