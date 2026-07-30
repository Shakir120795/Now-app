"""Notifications use-cases + fan-out helper for other modules."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.pagination import Page, PageParams, build_page
from app.features.auth.models import User
from app.features.notifications.models import Notification, NotificationBroadcast
from app.features.notifications.repository import NotificationRepository
from app.features.notifications.schemas import (
    BroadcastIn,
    NotificationOut,
    PreferencesIn,
    PreferencesOut,
)

_DEFAULT_PREFS = {"push": True, "email": True, "sms": True, "whatsapp": False}


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)

    async def list(self, user: User, params: PageParams) -> Page[NotificationOut]:
        rows = await self.repo.list_for_user(user.id, params.offset, params.limit)
        items = [NotificationOut(id=n.id, channel=n.channel, title=n.title, body=n.body,
                                 data=n.data, read_at=n.read_at, created_at=n.created_at) for n in rows]
        return build_page(items, len(items) + params.offset, params)

    async def mark_read(self, user: User, notif_id: uuid.UUID) -> None:
        n = await self.repo.get(notif_id, user.id)
        if n is None:
            raise NotFound("Notification not found.")
        await self.repo.mark_read(n)

    async def get_preferences(self, user: User) -> PreferencesOut:
        prefs = {**_DEFAULT_PREFS, **(user.preferences or {}).get("notifications", {})}
        return PreferencesOut(**prefs)

    async def set_preferences(self, user: User, body: PreferencesIn) -> PreferencesOut:
        patch = {k: v for k, v in body.model_dump().items() if v is not None}
        saved = await self.repo.set_preferences(user, patch)
        return PreferencesOut(**{**_DEFAULT_PREFS, **saved})

    async def create_broadcast(self, actor: User, body: BroadcastIn) -> dict:
        b = await self.repo.add_broadcast(NotificationBroadcast(
            title=body.title, body=body.body, channel=body.channel,
            audience=body.audience, created_by=actor.id,
        ))
        # Actual delivery (FCM/email/SMS) is dispatched by the worker in app/workers.
        return {"id": str(b.id), "status": "queued"}

    # ----- fan-out helper used by other modules (orders, payments) -----
    async def notify(self, user_id: uuid.UUID, title: str, body: str,
                     channel: str = "push", data: dict | None = None) -> None:
        await self.repo.create(Notification(
            user_id=user_id, channel=channel, title=title, body=body, data=data, status="sent"
        ))
