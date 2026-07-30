"""Catalog DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


# ---------- categories ----------
class CategoryBase(BaseModel):
    name: str = Field(max_length=160)
    slug: str = Field(max_length=180)
    description: str | None = None
    image_url: str | None = None
    icon_url: str | None = None
    sort_order: int = 0
    is_active: bool = True
    parent_id: uuid.UUID | None = None
    seo_title: str | None = None
    seo_description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    id: uuid.UUID
    children: list["CategoryOut"] = []


# ---------- variants / addons / media ----------
class InventoryOut(BaseModel):
    quantity: int
    available: int
    track: bool


class VariantOut(BaseModel):
    id: uuid.UUID
    name: str
    sku: str | None
    price_amount: int
    compare_at_amount: int | None
    is_active: bool
    inventory: InventoryOut | None = None


class AddonOut(BaseModel):
    id: uuid.UUID
    name: str
    price_amount: int
    is_active: bool


class AddonGroupOut(BaseModel):
    id: uuid.UUID
    name: str
    min_select: int
    max_select: int
    is_required: bool
    addons: list[AddonOut] = []


class MediaOut(BaseModel):
    id: uuid.UUID
    url: str
    thumb_url: str | None
    type: str
    is_primary: bool


# ---------- products ----------
class ProductCard(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    short_description: str | None
    brand: str | None
    is_veg: bool | None
    rating_avg: float
    rating_count: int
    primary_image: str | None = None
    price_from: int | None = None


class ProductDetail(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID | None
    name: str
    slug: str
    short_description: str | None
    description: str | None
    ingredients: str | None
    nutrition: dict | None
    brand: str | None
    is_veg: bool | None
    delivery_eta_minutes: int | None
    rating_avg: float
    rating_count: int
    media: list[MediaOut] = []
    variants: list[VariantOut] = []
    addon_groups: list[AddonGroupOut] = []


class ProductCreate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str = Field(max_length=200)
    slug: str = Field(max_length=220)
    short_description: str | None = None
    description: str | None = None
    ingredients: str | None = None
    nutrition: dict | None = None
    brand: str | None = None
    is_veg: bool | None = None
    tax_class_id: uuid.UUID | None = None
    delivery_eta_minutes: int | None = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = None
    short_description: str | None = None
    description: str | None = None
    ingredients: str | None = None
    nutrition: dict | None = None
    brand: str | None = None
    is_veg: bool | None = None
    tax_class_id: uuid.UUID | None = None
    delivery_eta_minutes: int | None = None
    is_active: bool | None = None


class VariantCreate(BaseModel):
    name: str = Field(max_length=160)
    sku: str | None = None
    price_amount: int = Field(ge=0)
    compare_at_amount: int | None = None
    initial_quantity: int = 0
