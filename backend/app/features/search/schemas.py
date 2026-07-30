"""Search DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.features.catalog.schemas import ProductCard


class SearchResults(BaseModel):
    query: str
    products: list[ProductCard] = []
    categories: list[dict] = []  # {id, name, slug}


class Suggestion(BaseModel):
    text: str
    type: str  # product | category | query


class SuggestOut(BaseModel):
    suggestions: list[Suggestion] = []


class TrendingOut(BaseModel):
    queries: list[str] = []
