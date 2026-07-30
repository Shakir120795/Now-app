"""Reviews data access + product rating aggregation."""
from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reviews.models import Review, ReviewMedia


class ReviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def has_delivered_purchase(self, user_id: uuid.UUID, product_id: uuid.UUID) -> bool:
        row = (await self.db.execute(
            text(
                """
                SELECT 1 FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE o.user_id = :uid AND oi.product_id = :pid AND o.status = 'delivered'
                LIMIT 1
                """
            ),
            {"uid": str(user_id), "pid": str(product_id)},
        )).first()
        return row is not None

    async def existing_review(self, user_id: uuid.UUID, product_id: uuid.UUID) -> Review | None:
        res = await self.db.execute(
            select(Review).where(Review.user_id == user_id, Review.product_id == product_id)
        )
        return res.scalar_one_or_none()

    async def add_review(self, review: Review, media_urls: list[str]) -> Review:
        self.db.add(review)
        await self.db.flush()
        for url in media_urls:
            self.db.add(ReviewMedia(review_id=review.id, url=url))
        await self.db.flush()
        return review

    async def get_review(self, review_id: uuid.UUID) -> Review | None:
        return await self.db.get(Review, review_id)

    async def list_for_product(self, product_id: uuid.UUID, offset: int, limit: int) -> list[Review]:
        res = await self.db.execute(
            select(Review)
            .where(Review.product_id == product_id, Review.status == "published")
            .order_by(Review.created_at.desc())
            .offset(offset).limit(limit)
        )
        return list(res.scalars().all())

    async def media_for(self, review_id: uuid.UUID) -> list[str]:
        res = await self.db.execute(select(ReviewMedia.url).where(ReviewMedia.review_id == review_id))
        return [r[0] for r in res.all()]

    async def delete_review(self, review: Review) -> None:
        await self.db.delete(review)
        await self.db.flush()

    async def recompute_rating(self, product_id: uuid.UUID) -> None:
        """Recalculate products.rating_avg / rating_count from published reviews."""
        await self.db.execute(
            text(
                """
                UPDATE products p SET
                    rating_avg = COALESCE(sub.avg, 0),
                    rating_count = COALESCE(sub.cnt, 0)
                FROM (
                    SELECT product_id, round(avg(rating)::numeric, 2) AS avg, count(*) AS cnt
                    FROM reviews WHERE product_id = :pid AND status = 'published'
                    GROUP BY product_id
                ) sub
                WHERE p.id = :pid
                """
            ),
            {"pid": str(product_id)},
        )
        # If no reviews remain, zero it out.
        await self.db.execute(
            text(
                """
                UPDATE products SET rating_avg = 0, rating_count = 0
                WHERE id = :pid AND NOT EXISTS (
                    SELECT 1 FROM reviews WHERE product_id = :pid AND status = 'published'
                )
                """
            ),
            {"pid": str(product_id)},
        )
