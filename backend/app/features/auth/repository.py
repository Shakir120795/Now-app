"""Data access for identity/auth. All SQL lives here."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import OtpRequest, RefreshToken, Role, User, UserRole


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ----- users -----
    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_user_by_phone(self, phone: str) -> User | None:
        res = await self.db.execute(select(User).where(User.phone == phone))
        return res.scalar_one_or_none()

    async def create_user(self, *, phone: str | None, is_guest: bool = False) -> User:
        user = User(
            phone=phone,
            is_guest=is_guest,
            referral_code=self._new_referral_code(),
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def promote_guest(self, user: User, phone: str) -> User:
        user.is_guest = False
        user.phone = phone
        await self.db.flush()
        return user

    # ----- otp -----
    async def add_otp(self, otp: OtpRequest) -> OtpRequest:
        self.db.add(otp)
        await self.db.flush()
        return otp

    async def latest_active_otp(self, phone: str) -> OtpRequest | None:
        res = await self.db.execute(
            select(OtpRequest)
            .where(OtpRequest.phone == phone, OtpRequest.consumed_at.is_(None))
            .order_by(OtpRequest.created_at.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def consume_otp(self, otp: OtpRequest) -> None:
        otp.consumed_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def bump_otp_attempts(self, otp: OtpRequest) -> None:
        otp.attempts += 1
        await self.db.flush()

    # ----- refresh tokens -----
    async def store_refresh(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_refresh_by_hash(self, token_hash: str) -> RefreshToken | None:
        res = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return res.scalar_one_or_none()

    async def revoke_refresh(self, token: RefreshToken, replaced_by: uuid.UUID | None = None) -> None:
        token.revoked_at = datetime.now(timezone.utc)
        token.replaced_by = replaced_by
        await self.db.flush()

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )

    # ----- roles -----
    async def assign_role(self, user_id: uuid.UUID, role_name: str) -> None:
        res = await self.db.execute(select(Role).where(Role.name == role_name))
        role = res.scalar_one_or_none()
        if role:
            self.db.add(UserRole(user_id=user_id, role_id=role.id))
            await self.db.flush()

    @staticmethod
    def _new_referral_code() -> str:
        return uuid.uuid4().hex[:8].upper()
