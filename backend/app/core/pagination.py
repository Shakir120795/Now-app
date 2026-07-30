"""Pagination / sorting helpers shared by list endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


@dataclass
class PageParams:
    page: int = Query(1, ge=1)
    page_size: int = Query(20, ge=1, le=100)
    sort: str | None = Query(None, description="comma fields, '-' prefix = desc")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class Page(BaseModel, Generic[T]):
    data: list[T]
    meta: PageMeta


def build_page(items: list[T], total: int, params: PageParams) -> Page[T]:
    total_pages = (total + params.page_size - 1) // params.page_size if params.page_size else 0
    return Page[T](
        data=items,
        meta=PageMeta(
            page=params.page,
            page_size=params.page_size,
            total=total,
            total_pages=total_pages,
        ),
    )
