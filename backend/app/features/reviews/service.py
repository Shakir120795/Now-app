"""Reviews use-cases (verified purchase + rating aggregation)."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, Forbidden, NotFound
from app.core.pagination import Page, PageParams, build_page
from app.features.auth.models import User
from app.features.reviews.models import Review
from app.features.reviews.repository import ReviewRepository
from app.features.reviews.schemas import ReviewCreate, ReviewOut, ReviewUpdate


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReviewRepository(db)

    async def create(self, user: User, product_id: uuid.UUID, body: ReviewCreate) -> ReviewOut:
        if not await self.repo.has_delivered_purchase(user.id, product_id):
            raise Forbidden("Only verified purchasers can review this product.")
        if await self.repo.existing_review(user.id, product_id):
            raise Conflict("You have already reviewed this product.")
        review = Review(
            product_id=product_id, user_id=user.id, rating=body.rating,
            title=body.title, body=body.body,
        )
        await self.repo.add_review(review, body.media_urls)
        await self.repo.recompute_rating(product_id)
        return await self._out(review)

    async def update(self, user: User, review_id: uuid.UUID, body: ReviewUpdate) -> ReviewOut:
        review = await self.repo.get_review(review_id)
        if review is None:
            raise NotFound("Review not found.")
        if review.user_id != user.id:
            raise Forbidden("Not your review.")
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(review, k, v)
        await self.db.flush()
        await self.repo.recompute_rating(review.product_id)
        return await self._out(review)

    async def delete(self, user: User, review_id: uuid.UUID) -> None:
        review = await self.repo.get_review(review_id)
        if review is None:
            raise NotFound("Review not found.")
        if review.user_id != user.id:
            raise Forbidden("Not your review.")
        product_id = review.product_id
        await self.repo.delete_review(review)
        await self.repo.recompute_rating(product_id)

    async def list_for_product(self, product_id: uuid.UUID, params: PageParams) -> Page[ReviewOut]:
        reviews = await self.repo.list_for_product(product_id, params.offset, params.limit)
        items = [await self._out(r) for r in reviews]
        return build_page(items, len(items) + params.offset, params)

    async def _out(self, r: Review) -> ReviewOut:
        media = await self.repo.media_for(r.id)
        return ReviewOut(id=r.id, product_id=r.product_id, rating=r.rating, title=r.title,
                         body=r.body, created_at=r.created_at, media=media)
