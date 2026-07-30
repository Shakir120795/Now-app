"""Search use-cases: live search, suggestions, trending."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.service import _primary_image
from app.features.catalog.schemas import ProductCard
from app.features.search.repository import SearchRepository
from app.features.search.schemas import (
    SearchResults,
    Suggestion,
    SuggestOut,
    TrendingOut,
)


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SearchRepository(db)

    async def search(self, q: str, user_id: uuid.UUID | None) -> SearchResults:
        q = q.strip()
        if not q:
            return SearchResults(query=q)
        products = await self.repo.search_products(q)
        categories = await self.repo.search_categories(q)
        await self.repo.log_query(user_id, q, len(products))
        return SearchResults(
            query=q,
            products=[
                ProductCard(
                    id=p.id, name=p.name, slug=p.slug, short_description=p.short_description,
                    brand=p.brand, is_veg=p.is_veg, rating_avg=float(p.rating_avg),
                    rating_count=p.rating_count, primary_image=_primary_image(p),
                    price_from=min((v.price_amount for v in p.variants if v.is_active), default=None),
                )
                for p in products
            ],
            categories=[{"id": str(c.id), "name": c.name, "slug": c.slug} for c in categories],
        )

    async def suggest(self, q: str) -> SuggestOut:
        q = q.strip()
        if len(q) < 2:
            return SuggestOut()
        products = await self.repo.search_products(q, limit=6)
        categories = await self.repo.search_categories(q, limit=4)
        out = [Suggestion(text=p.name, type="product") for p in products]
        out += [Suggestion(text=c.name, type="category") for c in categories]
        return SuggestOut(suggestions=out)

    async def trending(self) -> TrendingOut:
        return TrendingOut(queries=await self.repo.trending())
