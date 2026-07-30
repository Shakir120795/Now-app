"""Reviews DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=160)
    body: str | None = None
    media_urls: list[str] = []


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    title: str | None = Field(default=None, max_length=160)
    body: str | None = None


class ReviewOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    rating: int
    title: str | None
    body: str | None
    author: str | None = None
    created_at: datetime
    media: list[str] = []
