"""Notifications transport."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_customer, require_permission
from app.core.pagination import Page, PageParams
from app.db.session import get_db
from app.features.auth.models import User
from app.features.notifications.schemas import (
    BroadcastIn,
    NotificationOut,
    PreferencesIn,
    PreferencesOut,
)
from app.features.notifications.service import NotificationService

router = APIRouter(tags=["notifications"])


@router.get("/me/notifications", response_model=Page[NotificationOut])
async def my_notifications(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db),
):
    return await NotificationService(db).list(user, PageParams(page=page, page_size=page_size))


@router.post("/me/notifications/{notif_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(notif_id: uuid.UUID, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    await NotificationService(db).mark_read(user, notif_id)


@router.get("/me/notification-preferences", response_model=PreferencesOut)
async def get_prefs(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await NotificationService(db).get_preferences(user)


@router.patch("/me/notification-preferences", response_model=PreferencesOut)
async def set_prefs(body: PreferencesIn, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await NotificationService(db).set_preferences(user, body)


admin_router = APIRouter(prefix="/admin", tags=["admin:notifications"])


@admin_router.post("/broadcasts", status_code=201)
async def create_broadcast(body: BroadcastIn, actor: User = Depends(require_permission("notification.send")), db: AsyncSession = Depends(get_db)):
    return await NotificationService(db).create_broadcast(actor, body)
