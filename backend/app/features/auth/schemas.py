"""Auth request/response DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class OtpRequestIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20, pattern=r"^\+?[0-9]{8,15}$")


class OtpRequestOut(BaseModel):
    request_id: uuid.UUID
    expires_in: int


class OtpVerifyIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    code: str = Field(min_length=4, max_length=8)
    guest_token: str | None = None


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    phone: str | None
    email: str | None
    full_name: str | None
    is_guest: bool
    referral_code: str | None
    default_locale: str
    roles: list[str] = []
    permissions: list[str] = []


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class GuestOut(BaseModel):
    access_token: str
    guest_token: str
    user: UserOut
