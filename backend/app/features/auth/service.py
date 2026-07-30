"""Auth use-cases: OTP login, guest, JWT refresh with rotation + reuse detection."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import Unauthorized
from app.core.rate_limit import enforce_rate_limit
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    generate_otp,
    hash_secret,
    hash_token,
    verify_secret,
)
from app.features.auth.models import OtpRequest, RefreshToken, User
from app.features.auth.repository import AuthRepository
from app.features.auth.schemas import GuestOut, TokenPair, UserOut


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user_out(user: User) -> UserOut:
    roles = [r.name for r in user.roles]
    perms = sorted({p.code for r in user.roles for p in r.permissions})
    return UserOut(
        id=user.id,
        phone=user.phone,
        email=user.email,
        full_name=user.full_name,
        is_guest=user.is_guest,
        referral_code=user.referral_code,
        default_locale=user.default_locale,
        roles=roles,
        permissions=perms,
    )


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuthRepository(db)

    # ---------------- OTP request ----------------
    async def request_otp(self, phone: str, ip: str | None) -> tuple[uuid.UUID, int]:
        # rate limit: max 5 requests / 10 min per phone
        await enforce_rate_limit(f"otp:{phone}", limit=5, window_seconds=600)
        code = generate_otp()
        otp = OtpRequest(
            phone=phone,
            code_hash=hash_secret(code),
            ip=ip,
            expires_at=_now() + timedelta(seconds=settings.otp_ttl_seconds),
        )
        await self.repo.add_otp(otp)
        # Phase 1.12 wires the real SMS provider; until then, log/deliver via provider adapter.
        await self._deliver_otp(phone, code)
        return otp.id, settings.otp_ttl_seconds

    async def _deliver_otp(self, phone: str, code: str) -> None:
        # Replaced by services/sms/msg91.py adapter. Never returns the code to the client.
        if settings.debug:
            import structlog

            structlog.get_logger().info("otp.debug", phone=phone, code=code)

    # ---------------- OTP verify ----------------
    async def verify_otp(
        self, phone: str, code: str, guest_token: str | None, request_meta: dict
    ) -> TokenPair:
        otp = await self.repo.latest_active_otp(phone)
        if otp is None or otp.expires_at < _now():
            raise Unauthorized("OTP expired or not requested.")
        if otp.attempts >= settings.otp_max_attempts:
            raise Unauthorized("Too many incorrect attempts. Request a new OTP.")
        if not verify_secret(code, otp.code_hash):
            await self.repo.bump_otp_attempts(otp)
            raise Unauthorized("Incorrect OTP.")
        await self.repo.consume_otp(otp)

        user = await self.repo.get_user_by_phone(phone)
        if user is None:
            # If a guest session exists, promote it; else create fresh.
            guest = await self._guest_from_token(guest_token)
            if guest is not None:
                user = await self.repo.promote_guest(guest, phone)
            else:
                user = await self.repo.create_user(phone=phone, is_guest=False)
            await self.repo.assign_role(user.id, "customer")
            await self.db.refresh(user)

        access, refresh = await self._issue_tokens(user, family_id=None, meta=request_meta)
        return TokenPair(access_token=access, refresh_token=refresh, user=_user_out(user))

    async def _guest_from_token(self, guest_token: str | None) -> User | None:
        if not guest_token:
            return None
        rec = await self.repo.get_refresh_by_hash(hash_token(guest_token))
        if rec and rec.revoked_at is None:
            user = await self.repo.get_user_by_id(rec.user_id)
            if user and user.is_guest:
                return user
        return None

    # ---------------- Guest login ----------------
    async def guest_login(self, meta: dict) -> GuestOut:
        user = await self.repo.create_user(phone=None, is_guest=True)
        await self.db.refresh(user)
        access, guest_token = await self._issue_tokens(user, family_id=None, meta=meta)
        return GuestOut(access_token=access, guest_token=guest_token, user=_user_out(user))

    # ---------------- Refresh (rotation + reuse detection) ----------------
    async def refresh(self, refresh_token: str, meta: dict) -> TokenPair:
        rec = await self.repo.get_refresh_by_hash(hash_token(refresh_token))
        if rec is None:
            raise Unauthorized("Invalid refresh token.")
        if rec.revoked_at is not None:
            # Reuse of a rotated/revoked token → compromise: kill the whole family.
            await self.repo.revoke_family(rec.family_id)
            raise Unauthorized("Refresh token reuse detected. Please log in again.")
        if rec.expires_at < _now():
            raise Unauthorized("Refresh token expired.")

        user = await self.repo.get_user_by_id(rec.user_id)
        if user is None:
            raise Unauthorized("User no longer exists.")

        access, new_refresh = await self._issue_tokens(user, family_id=rec.family_id, meta=meta)
        # find the freshly stored token to link replacement
        new_rec = await self.repo.get_refresh_by_hash(hash_token(new_refresh))
        await self.repo.revoke_refresh(rec, replaced_by=new_rec.id if new_rec else None)
        return TokenPair(access_token=access, refresh_token=new_refresh, user=_user_out(user))

    # ---------------- Logout ----------------
    async def logout(self, refresh_token: str) -> None:
        rec = await self.repo.get_refresh_by_hash(hash_token(refresh_token))
        if rec and rec.revoked_at is None:
            await self.repo.revoke_refresh(rec)

    async def logout_all(self, user: User) -> None:
        await self.repo.revoke_all_for_user(user.id)

    # ---------------- token issuance ----------------
    async def _issue_tokens(
        self, user: User, family_id: uuid.UUID | None, meta: dict
    ) -> tuple[str, str]:
        access = create_access_token(str(user.id), extra={"guest": user.is_guest})
        raw_refresh = generate_opaque_token()
        rec = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            family_id=family_id or uuid.uuid4(),
            user_agent=meta.get("user_agent"),
            ip=meta.get("ip"),
            expires_at=_now() + timedelta(days=settings.refresh_token_ttl_days),
        )
        await self.repo.store_refresh(rec)
        return access, raw_refresh
