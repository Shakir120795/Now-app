"""Users, addresses, devices transport."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_customer, get_current_user, require_permission
from app.core.pagination import PageParams, build_page
from app.db.session import get_db
from app.features.auth.models import User
from app.features.auth.schemas import UserOut
from app.features.auth.service import _user_out
from app.features.users.repository import UserRepository
from app.features.users.schemas import AddressIn, AddressOut, DeviceIn, ProfileUpdate
from app.features.users.service import UserService

router = APIRouter(tags=["users"])
admin_router = APIRouter(prefix="/admin", tags=["admin:users"])


@admin_router.get("/users")
async def admin_list_users(
    q: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_permission("user.read")), db: AsyncSession = Depends(get_db),
):
    params = PageParams(page=page, page_size=page_size)
    users, total = await UserRepository(db).list_users(q, params.offset, params.limit)
    data = [{"id": str(u.id), "full_name": u.full_name, "phone": u.phone,
             "email": u.email, "status": u.status, "created_at": u.created_at.isoformat()} for u in users]
    return build_page(data, total, params).model_dump()


@router.patch("/me", response_model=UserOut)
async def update_me(body: ProfileUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    updated = await UserService(db).update_profile(user, body)
    return _user_out(updated)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    await UserService(db).delete_account(user)


@router.get("/me/addresses", response_model=list[AddressOut])
async def list_addresses(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await UserService(db).list_addresses(user)


@router.post("/me/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
async def create_address(body: AddressIn, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await UserService(db).create_address(user, body)


@router.patch("/me/addresses/{address_id}", response_model=AddressOut)
async def update_address(address_id: uuid.UUID, body: AddressIn, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await UserService(db).update_address(user, address_id, body)


@router.delete("/me/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(address_id: uuid.UUID, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    await UserService(db).delete_address(user, address_id)


@router.post("/me/addresses/{address_id}/default", status_code=status.HTTP_204_NO_CONTENT)
async def set_default_address(address_id: uuid.UUID, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    await UserService(db).set_default_address(user, address_id)


@router.post("/me/devices", status_code=status.HTTP_204_NO_CONTENT)
async def register_device(body: DeviceIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await UserService(db).register_device(user, body.fcm_token, body.platform)


@router.delete("/me/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device(device_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await UserService(db).unregister_device(user, device_id)
