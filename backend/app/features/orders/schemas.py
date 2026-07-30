"""Orders DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PlaceOrderIn(BaseModel):
    address_id: uuid.UUID
    payment_method: str = Field(pattern="^(cod|razorpay|phonepe|upi|wallet)$")
    coupon_code: str | None = None
    use_wallet: bool = False
    tip: int = Field(default=0, ge=0)
    delivery_slot_start: datetime | None = None
    delivery_slot_end: datetime | None = None
    is_gift: bool = False
    gift_message: str | None = Field(default=None, max_length=500)
    customer_notes: str | None = Field(default=None, max_length=500)


class OrderItemOut(BaseModel):
    product_name: str
    variant_name: str | None
    unit_price_amount: int
    quantity: int
    line_total: int
    addons: list[dict] = []


class StatusEvent(BaseModel):
    to_status: str
    note: str | None
    at: datetime


class OrderOut(BaseModel):
    id: uuid.UUID
    order_number: str
    status: str
    payment_status: str
    currency: str
    subtotal: int
    discount_total: int
    membership_discount: int
    tax_total: int
    shipping_total: int
    tip_amount: int
    wallet_applied: int
    grand_total: int
    items: list[OrderItemOut] = []
    timeline: list[StatusEvent] = []
    created_at: datetime


class OrderCard(BaseModel):
    id: uuid.UUID
    order_number: str
    status: str
    grand_total: int
    created_at: datetime


class PlaceOrderOut(BaseModel):
    order: OrderOut
    payment: dict  # {provider, method, amount, requires_action}


class StatusUpdateIn(BaseModel):
    to_status: str
    note: str | None = None
