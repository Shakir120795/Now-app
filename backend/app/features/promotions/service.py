"""Promotions use-cases: coupons, membership, referral, rewards."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, NotFound
from app.features.auth.models import User
from app.features.promotions.models import Coupon, Membership, MembershipPlan
from app.features.promotions.repository import PromotionsRepository
from app.features.promotions.schemas import (
    CouponCreate,
    CouponOut,
    MembershipOut,
    PlanOut,
    ReferralOut,
    RewardsOut,
    RewardTxnOut,
    SubscribeIn,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _coupon_out(c: Coupon) -> CouponOut:
    return CouponOut(id=c.id, code=c.code, type=c.type, value=c.value, max_discount=c.max_discount,
                     min_order=c.min_order, ends_at=c.ends_at, is_active=c.is_active)


def _plan_out(p: MembershipPlan) -> PlanOut:
    return PlanOut(id=p.id, name=p.name, description=p.description, price_amount=p.price_amount,
                   duration_days=p.duration_days, benefits=p.benefits, is_active=p.is_active)


def _membership_out(m: Membership) -> MembershipOut:
    return MembershipOut(id=m.id, plan_id=m.plan_id, status=m.status, starts_at=m.starts_at,
                         ends_at=m.ends_at, auto_renew=m.auto_renew)


class PromotionsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PromotionsRepository(db)

    # ----- coupons -----
    async def available(self) -> list[CouponOut]:
        return [_coupon_out(c) for c in await self.repo.available_coupons()]

    async def create_coupon(self, body: CouponCreate) -> CouponOut:
        c = await self.repo.add_coupon(Coupon(**body.model_dump()))
        return _coupon_out(c)

    # ----- membership -----
    async def plans(self) -> list[PlanOut]:
        return [_plan_out(p) for p in await self.repo.active_plans()]

    async def subscribe(self, user: User, body: SubscribeIn) -> MembershipOut:
        plan = await self.repo.get_plan(body.plan_id)
        if plan is None or not plan.is_active:
            raise NotFound("Membership plan not available.")
        # NOTE: payment gating for paid plans is wired via the payment flow; a pending
        # membership is activated on payment success. Free plans activate immediately.
        now = _now()
        status = "active" if plan.price_amount == 0 else "pending"
        membership = Membership(
            user_id=user.id, plan_id=plan.id, status=status,
            starts_at=now if status == "active" else None,
            ends_at=now + timedelta(days=plan.duration_days) if status == "active" else None,
            auto_renew=body.auto_renew,
        )
        await self.repo.add_membership(membership)
        return _membership_out(membership)

    async def my_membership(self, user: User) -> MembershipOut | None:
        m = await self.repo.current_membership(user.id)
        return _membership_out(m) if m else None

    # ----- referral -----
    async def referral(self, user: User) -> ReferralOut:
        total, success, reward = await self.repo.referral_stats(user.id)
        return ReferralOut(code=user.referral_code, total_referred=total,
                           successful=success, total_reward=reward)

    # ----- rewards -----
    async def rewards(self, user: User) -> RewardsOut:
        txns = await self.repo.reward_transactions(user.id)
        return RewardsOut(
            balance=user.reward_points_balance,
            transactions=[RewardTxnOut(id=t.id, points=t.points, type=t.type,
                                       note=t.note, created_at=t.created_at) for t in txns],
        )
