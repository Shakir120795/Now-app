"""Notifications data access."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.features.auth.models import User
from app.features.notifications.models import Notification, NotificationBroadcast


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: uuid.UUID, offset: int, limit: int) -> list[Notification]:
        res = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(offset).limit(limit)
        )
        return list(res.scalars().all())

    async def get(self, notif_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        res = await self.db.execute(
            select(Notification).where(Notification.id == notif_id, Notification.user_id == user_id)
        )
        return res.scalar_one_or_none()

    async def mark_read(self, notif: Notification) -> None:
        notif.read_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def create(self, notif: Notification) -> Notification:
        self.db.add(notif)
        await self.db.flush()
        return notif

    async def set_preferences(self, user: User, prefs: dict) -> dict:
        current = dict(user.preferences or {})
        current["notifications"] = {**current.get("notifications", {}), **prefs}
        user.preferences = current
        flag_modified(user, "preferences")
        await self.db.flush()
        return current["notifications"]

    async def add_broadcast(self, broadcast: NotificationBroadcast) -> NotificationBroadcast:
        self.db.add(broadcast)
        await self.db.flush()
        return broadcast
