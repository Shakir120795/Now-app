"""Promotions transport: coupons, membership, referral, rewards."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_customer, require_permission
from app.db.session import get_db
from app.features.auth.models import User
from app.features.promotions.schemas import (
    CouponCreate,
    CouponOut,
    MembershipOut,
    PlanOut,
    ReferralOut,
    RewardsOut,
    SubscribeIn,
)
from app.features.promotions.service import PromotionsService

router = APIRouter(tags=["promotions"])


@router.get("/coupons/available", response_model=list[CouponOut])
async def available_coupons(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await PromotionsService(db).available()


@router.get("/membership/plans", response_model=list[PlanOut])
async def plans(db: AsyncSession = Depends(get_db)):
    return await PromotionsService(db).plans()


@router.post("/membership/subscribe", response_model=MembershipOut, status_code=201)
async def subscribe(body: SubscribeIn, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await PromotionsService(db).subscribe(user, body)


@router.get("/me/membership", response_model=MembershipOut | None)
async def my_membership(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await PromotionsService(db).my_membership(user)


@router.get("/me/referral", response_model=ReferralOut)
async def my_referral(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await PromotionsService(db).referral(user)


@router.get("/me/rewards", response_model=RewardsOut)
async def my_rewards(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await PromotionsService(db).rewards(user)


admin_router = APIRouter(prefix="/admin", tags=["admin:promotions"])


@admin_router.post("/coupons", response_model=CouponOut, status_code=201)
async def create_coupon(body: CouponCreate, _: User = Depends(require_permission("coupon.manage")), db: AsyncSession = Depends(get_db)):
    return await PromotionsService(db).create_coupon(body)
