"""Payments DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class IntentOut(BaseModel):
    provider: str
    provider_ref: str
    amount: int
    currency: str = "INR"
    extra: dict = {}


class VerifyIn(BaseModel):
    order_id: uuid.UUID
    provider: str
    # Razorpay: razorpay_order_id/payment_id/signature ; PhonePe: response
    payload: dict = {}
    signature: str | None = None


class VerifyOut(BaseModel):
    order_id: uuid.UUID
    payment_status: str
    order_status: str


class SavedCardIn(BaseModel):
    provider: str
    provider_token: str
    brand: str | None = None
    last4: str | None = Field(default=None, max_length=4)
    exp_month: int | None = None
    exp_year: int | None = None
    is_default: bool = False


class SavedCardOut(BaseModel):
    id: uuid.UUID
    provider: str
    brand: str | None
    last4: str | None
    exp_month: int | None
    exp_year: int | None
    is_default: bool
