"""Data access for profile, addresses, devices."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import Device, User
from app.features.users.models import Address


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ----- admin -----
    async def list_users(self, q: str | None, offset: int, limit: int) -> tuple[list[User], int]:
        from sqlalchemy import func, or_, select as _select, text as _text
        base = _select(User).where(User.is_guest.is_(False))
        if q:
            like = f"%{q.lower()}%"
            base = base.where(or_(func.lower(User.full_name).like(like), User.phone.like(like)))
        total = (await self.db.execute(_select(func.count()).select_from(base.subquery()))).scalar_one()
        res = await self.db.execute(base.order_by(User.created_at.desc()).offset(offset).limit(limit))
        return list(res.scalars().all()), int(total)

    # ----- profile -----
    async def update_profile(self, user: User, data: dict) -> User:
        for k, v in data.items():
            if v is not None:
                setattr(user, k, v)
        await self.db.flush()
        return user

    async def soft_delete_user(self, user: User) -> None:
        user.status = "deleted"
        user.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    # ----- addresses -----
    async def list_addresses(self, user_id: uuid.UUID) -> list[Address]:
        res = await self.db.execute(
            select(Address)
            .where(Address.user_id == user_id, Address.deleted_at.is_(None))
            .order_by(Address.is_default.desc(), Address.created_at.desc())
        )
        return list(res.scalars().all())

    async def get_address(self, user_id: uuid.UUID, address_id: uuid.UUID) -> Address | None:
        res = await self.db.execute(
            select(Address).where(
                Address.id == address_id,
                Address.user_id == user_id,
                Address.deleted_at.is_(None),
            )
        )
        return res.scalar_one_or_none()

    async def create_address(self, user_id: uuid.UUID, data: dict) -> Address:
        if data.get("is_default"):
            await self._clear_default(user_id)
        addr = Address(user_id=user_id, **data)
        self.db.add(addr)
        await self.db.flush()
        return addr

    async def update_address(self, addr: Address, data: dict) -> Address:
        if data.get("is_default"):
            await self._clear_default(addr.user_id)
        for k, v in data.items():
            setattr(addr, k, v)
        await self.db.flush()
        return addr

    async def delete_address(self, addr: Address) -> None:
        addr.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def set_default(self, addr: Address) -> None:
        await self._clear_default(addr.user_id)
        addr.is_default = True
        await self.db.flush()

    async def _clear_default(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(Address).where(Address.user_id == user_id).values(is_default=False)
        )

    # ----- devices -----
    async def upsert_device(self, user_id: uuid.UUID, fcm_token: str, platform: str) -> Device:
        res = await self.db.execute(
            select(Device).where(Device.user_id == user_id, Device.fcm_token == fcm_token)
        )
        device = res.scalar_one_or_none()
        if device is None:
            device = Device(user_id=user_id, fcm_token=fcm_token, platform=platform)
            self.db.add(device)
        else:
            device.platform = platform
            device.last_seen_at = datetime.now(timezone.utc)
        await self.db.flush()
        return device

    async def delete_device(self, user_id: uuid.UUID, device_id: uuid.UUID) -> None:
        res = await self.db.execute(
            select(Device).where(Device.id == device_id, Device.user_id == user_id)
        )
        device = res.scalar_one_or_none()
        if device:
            await self.db.delete(device)
            await self.db.flush()
