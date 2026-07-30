"""Delivery DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AssignmentOut(BaseModel):
    order_id: uuid.UUID
    order_number: str
    status: str
    ship_line1: str | None
    ship_city: str | None
    ship_pincode: str | None
    grand_total: int
    assigned: bool


class AdvanceStatusIn(BaseModel):
    to_status: str = Field(pattern="^(packed|out_for_delivery)$")


class DeliverIn(BaseModel):
    otp: str = Field(min_length=4, max_length=8)


class AvailabilityIn(BaseModel):
    status: str = Field(pattern="^(available|offline)$")
    lat: float | None = None
    lng: float | None = None


class EarningOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID | None
    amount: int
    type: str
    created_at: datetime


class EarningsSummaryOut(BaseModel):
    total: int
    count: int
    earnings: list[EarningOut] = []


class AssignAgentIn(BaseModel):
    agent_id: uuid.UUID
