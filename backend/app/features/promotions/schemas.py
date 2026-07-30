"""Promotions DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CouponOut(BaseModel):
    id: uuid.UUID
    code: str
    type: str
    value: int
    max_discount: int | None
    min_order: int
    ends_at: datetime | None
    is_active: bool


class CouponCreate(BaseModel):
    code: str = Field(max_length=40)
    type: str = Field(pattern="^(percentage|fixed|free_delivery)$")
    value: int = Field(default=0, ge=0)
    max_discount: int | None = None
    min_order: int = Field(default=0, ge=0)
    usage_limit_total: int | None = None
    usage_limit_per_user: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = True


class PlanOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    price_amount: int
    duration_days: int
    benefits: dict | None
    is_active: bool


class SubscribeIn(BaseModel):
    plan_id: uuid.UUID
    auto_renew: bool = False


class MembershipOut(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    auto_renew: bool


class ReferralOut(BaseModel):
    code: str | None
    total_referred: int
    successful: int
    total_reward: int


class RewardTxnOut(BaseModel):
    id: uuid.UUID
    points: int
    type: str
    note: str | None
    created_at: datetime


class RewardsOut(BaseModel):
    balance: int
    transactions: list[RewardTxnOut] = []
