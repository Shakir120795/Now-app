"""Search data access."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Category, Product
from app.features.search.models import SearchQuery


class SearchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_products(self, q: str, limit: int = 20) -> list[Product]:
        like = f"%{q.lower()}%"
        res = await self.db.execute(
            select(Product)
            .where(
                Product.deleted_at.is_(None),
                Product.is_active.is_(True),
                func.lower(Product.name).like(like),
            )
            .order_by(Product.rating_avg.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def search_categories(self, q: str, limit: int = 10) -> list[Category]:
        like = f"%{q.lower()}%"
        res = await self.db.execute(
            select(Category)
            .where(
                Category.deleted_at.is_(None),
                Category.is_active.is_(True),
                func.lower(Category.name).like(like),
            )
            .limit(limit)
        )
        return list(res.scalars().all())

    async def log_query(self, user_id: uuid.UUID | None, query: str, count: int) -> None:
        self.db.add(SearchQuery(user_id=user_id, query=query, results_count=count))
        await self.db.flush()

    async def trending(self, limit: int = 10) -> list[str]:
        # Most frequent non-empty queries over the recent window.
        res = await self.db.execute(
            select(SearchQuery.query, func.count().label("c"))
            .where(func.char_length(SearchQuery.query) >= 2)
            .group_by(SearchQuery.query)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [row[0] for row in res.all()]
