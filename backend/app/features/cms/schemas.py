"""CMS DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.features.catalog.schemas import ProductCard


class BannerOut(BaseModel):
    id: uuid.UUID
    title: str | None
    image_url: str
    placement: str
    target_type: str | None
    target_ref: str | None


class HomeSectionOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str | None
    items: list[ProductCard] = []
    banners: list[BannerOut] = []


class HomeLayoutOut(BaseModel):
    sections: list[HomeSectionOut] = []


class OnboardingSlideOut(BaseModel):
    id: uuid.UUID
    title: str | None
    subtitle: str | None
    image_url: str


class PageOut(BaseModel):
    slug: str
    title: str
    body: str | None


class BrandingOut(BaseModel):
    settings: dict = {}


class SettingIn(BaseModel):
    group_key: str = Field(max_length=48)
    key: str = Field(max_length=80)
    value: dict | list | str | int | float | bool | None


class BannerIn(BaseModel):
    title: str | None = None
    image_url: str
    placement: str = "hero"
    target_type: str | None = None
    target_ref: str | None = None
    sort_order: int = 0
    is_active: bool = True


class PageIn(BaseModel):
    slug: str = Field(max_length=120)
    title: str = Field(max_length=200)
    body: str | None = None
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")
