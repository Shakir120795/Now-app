"""Users & addresses use-cases."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.features.auth.models import User
from app.features.users.models import Address
from app.features.users.repository import UserRepository
from app.features.users.schemas import AddressIn, AddressOut, ProfileUpdate


def _address_out(a: Address) -> AddressOut:
    return AddressOut(
        id=a.id, label=a.label, recipient_name=a.recipient_name, phone=a.phone,
        line1=a.line1, line2=a.line2, landmark=a.landmark, city=a.city, state=a.state,
        pincode=a.pincode, country=a.country, lat=a.lat, lng=a.lng, is_default=a.is_default,
    )


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def update_profile(self, user: User, data: ProfileUpdate) -> User:
        return await self.repo.update_profile(user, data.model_dump(exclude_unset=True))

    async def delete_account(self, user: User) -> None:
        await self.repo.soft_delete_user(user)

    async def list_addresses(self, user: User) -> list[AddressOut]:
        return [_address_out(a) for a in await self.repo.list_addresses(user.id)]

    async def create_address(self, user: User, data: AddressIn) -> AddressOut:
        addr = await self.repo.create_address(user.id, data.model_dump())
        return _address_out(addr)

    async def update_address(self, user: User, address_id: uuid.UUID, data: AddressIn) -> AddressOut:
        addr = await self._require(user.id, address_id)
        addr = await self.repo.update_address(addr, data.model_dump())
        return _address_out(addr)

    async def delete_address(self, user: User, address_id: uuid.UUID) -> None:
        addr = await self._require(user.id, address_id)
        await self.repo.delete_address(addr)

    async def set_default_address(self, user: User, address_id: uuid.UUID) -> None:
        addr = await self._require(user.id, address_id)
        await self.repo.set_default(addr)

    async def register_device(self, user: User, fcm_token: str, platform: str) -> None:
        await self.repo.upsert_device(user.id, fcm_token, platform)

    async def unregister_device(self, user: User, device_id: uuid.UUID) -> None:
        await self.repo.delete_device(user.id, device_id)

    async def _require(self, user_id: uuid.UUID, address_id: uuid.UUID) -> Address:
        addr = await self.repo.get_address(user_id, address_id)
        if addr is None:
            raise NotFound("Address not found.")
        return addr
