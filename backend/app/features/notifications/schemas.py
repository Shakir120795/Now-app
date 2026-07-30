"""Notifications DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: uuid.UUID
    channel: str
    title: str | None
    body: str | None
    data: dict | None
    read_at: datetime | None
    created_at: datetime


class PreferencesIn(BaseModel):
    push: bool | None = None
    email: bool | None = None
    sms: bool | None = None
    whatsapp: bool | None = None


class PreferencesOut(BaseModel):
    push: bool = True
    email: bool = True
    sms: bool = True
    whatsapp: bool = False


class BroadcastIn(BaseModel):
    title: str
    body: str
    channel: str = "push"
    audience: dict | None = None
