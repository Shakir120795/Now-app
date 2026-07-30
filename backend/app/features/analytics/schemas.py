"""Analytics DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DashboardOut(BaseModel):
    revenue: int            # paid revenue, minor units
    orders: int
    new_customers: int
    avg_order_value: int
    delivered: int
    cancelled: int


class TimePoint(BaseModel):
    date: str
    revenue: int
    orders: int


class SalesSeriesOut(BaseModel):
    points: list[TimePoint] = []


class TopProduct(BaseModel):
    product_name: str
    units: int
    revenue: int


class TopProductsOut(BaseModel):
    products: list[TopProduct] = []


class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    created_at: datetime
