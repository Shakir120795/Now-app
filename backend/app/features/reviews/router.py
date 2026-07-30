"""Reviews transport."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_customer
from app.core.pagination import Page, PageParams
from app.db.session import get_db
from app.features.auth.models import User
from app.features.reviews.schemas import ReviewCreate, ReviewOut, ReviewUpdate
from app.features.reviews.service import ReviewService

router = APIRouter(tags=["reviews"])


@router.get("/products/{product_id}/reviews", response_model=Page[ReviewOut])
async def list_reviews(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await ReviewService(db).list_for_product(product_id, PageParams(page=page, page_size=page_size))


@router.post("/products/{product_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    product_id: uuid.UUID, body: ReviewCreate,
    user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db),
):
    return await ReviewService(db).create(user, product_id, body)


@router.patch("/me/reviews/{review_id}", response_model=ReviewOut)
async def update_review(
    review_id: uuid.UUID, body: ReviewUpdate,
    user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db),
):
    return await ReviewService(db).update(user, review_id, body)


@router.delete("/me/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: uuid.UUID, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db),
):
    await ReviewService(db).delete(user, review_id)
