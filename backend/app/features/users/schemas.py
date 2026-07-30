"""Users & addresses DTOs."""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    email: EmailStr | None = None
    default_locale: str | None = Field(default=None, max_length=8)


class AddressIn(BaseModel):
    label: str = Field(default="home", max_length=32)
    recipient_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=20)
    line1: str = Field(max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    landmark: str | None = Field(default=None, max_length=160)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    pincode: str | None = Field(default=None, max_length=12)
    country: str = Field(default="India", max_length=64)
    lat: Decimal | None = None
    lng: Decimal | None = None
    is_default: bool = False


class AddressOut(AddressIn):
    id: uuid.UUID


class DeviceIn(BaseModel):
    fcm_token: str
    platform: str = Field(max_length=16)
