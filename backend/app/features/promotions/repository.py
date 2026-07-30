"""Promotions data access."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.promotions.models import (
    Coupon,
    Membership,
    MembershipPlan,
    Referral,
    RewardTransaction,
)


class PromotionsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ----- coupons -----
    async def available_coupons(self) -> list[Coupon]:
        res = await self.db.execute(
            select(Coupon).where(Coupon.is_active.is_(True)).order_by(Coupon.min_order)
        )
        return list(res.scalars().all())

    async def add_coupon(self, coupon: Coupon) -> Coupon:
        self.db.add(coupon)
        await self.db.flush()
        return coupon

    async def get_coupon(self, coupon_id: uuid.UUID) -> Coupon | None:
        return await self.db.get(Coupon, coupon_id)

    # ----- membership -----
    async def active_plans(self) -> list[MembershipPlan]:
        res = await self.db.execute(
            select(MembershipPlan).where(MembershipPlan.is_active.is_(True)).order_by(MembershipPlan.sort_order)
        )
        return list(res.scalars().all())

    async def get_plan(self, plan_id: uuid.UUID) -> MembershipPlan | None:
        return await self.db.get(MembershipPlan, plan_id)

    async def add_plan(self, plan: MembershipPlan) -> MembershipPlan:
        self.db.add(plan)
        await self.db.flush()
        return plan

    async def add_membership(self, membership: Membership) -> Membership:
        self.db.add(membership)
        await self.db.flush()
        return membership

    async def current_membership(self, user_id: uuid.UUID) -> Membership | None:
        res = await self.db.execute(
            select(Membership)
            .where(Membership.user_id == user_id, Membership.status == "active")
            .order_by(Membership.ends_at.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()

    # ----- referral -----
    async def referral_stats(self, user_id: uuid.UUID) -> tuple[int, int, int]:
        total = (await self.db.execute(
            select(func.count()).select_from(Referral).where(Referral.referrer_id == user_id)
        )).scalar_one()
        success = (await self.db.execute(
            select(func.count()).select_from(Referral).where(
                Referral.referrer_id == user_id, Referral.status == "rewarded"
            )
        )).scalar_one()
        reward = (await self.db.execute(
            select(func.coalesce(func.sum(Referral.reward_amount), 0)).where(
                Referral.referrer_id == user_id, Referral.status == "rewarded"
            )
        )).scalar_one()
        return int(total), int(success), int(reward)

    # ----- rewards -----
    async def reward_transactions(self, user_id: uuid.UUID, limit: int = 50) -> list[RewardTransaction]:
        res = await self.db.execute(
            select(RewardTransaction)
            .where(RewardTransaction.user_id == user_id)
            .order_by(RewardTransaction.created_at.desc())
            .limit(limit)
        )
        return list(res.scalars().all())
