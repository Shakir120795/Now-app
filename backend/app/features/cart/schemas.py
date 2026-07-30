"""Cart DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class AddItemIn(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=99)
    addon_ids: list[uuid.UUID] = []
    notes: str | None = Field(default=None, max_length=255)


class UpdateItemIn(BaseModel):
    quantity: int = Field(ge=1, le=99)
    notes: str | None = Field(default=None, max_length=255)


class QuoteRequest(BaseModel):
    coupon_code: str | None = None
    use_wallet: bool = False
    tip: int = Field(default=0, ge=0)
    address_id: uuid.UUID | None = None   # resolves delivery zone / shipping


class ApplyCouponIn(BaseModel):
    code: str


class CartItemAddonOut(BaseModel):
    addon_id: uuid.UUID
    price_amount: int


class CartItemOut(BaseModel):
    id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str | None = None
    variant_name: str | None = None
    quantity: int
    unit_price_amount: int
    addons: list[CartItemAddonOut] = []
    line_total: int
    notes: str | None = None


class PricingQuoteOut(BaseModel):
    subtotal: int
    discount_total: int
    membership_discount: int
    tax_total: int
    shipping_total: int
    tip_amount: int
    wallet_applied: int
    grand_total: int
    coupon_applied: bool
    coupon_error: str | None = None
    currency: str = "INR"


class CartOut(BaseModel):
    id: uuid.UUID
    items: list[CartItemOut] = []
    quote: PricingQuoteOut
