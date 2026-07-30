"""Delivery data access."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.delivery.models import DeliveryAgent, DeliveryEarning
from app.features.orders.models import Order, OrderDelivery


class DeliveryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def agent_by_user(self, user_id: uuid.UUID) -> DeliveryAgent | None:
        res = await self.db.execute(select(DeliveryAgent).where(DeliveryAgent.user_id == user_id))
        return res.scalar_one_or_none()

    async def get_agent(self, agent_id: uuid.UUID) -> DeliveryAgent | None:
        return await self.db.get(DeliveryAgent, agent_id)

    async def delivery_for_order(self, order_id: uuid.UUID) -> OrderDelivery | None:
        res = await self.db.execute(select(OrderDelivery).where(OrderDelivery.order_id == order_id))
        return res.scalar_one_or_none()

    async def assignments(self, agent_id: uuid.UUID) -> list[tuple[Order, OrderDelivery]]:
        # Orders assigned to this agent, plus unassigned packed orders (available pool).
        res = await self.db.execute(
            select(Order, OrderDelivery)
            .join(OrderDelivery, OrderDelivery.order_id == Order.id)
            .where(
                Order.status.in_(("packed", "out_for_delivery")),
                (OrderDelivery.agent_id == agent_id) | (OrderDelivery.agent_id.is_(None)),
            )
            .order_by(Order.created_at.desc())
        )
        return list(res.all())

    async def order(self, order_id: uuid.UUID) -> Order | None:
        return await self.db.get(Order, order_id)

    async def add_earning(self, earning: DeliveryEarning) -> None:
        self.db.add(earning)
        await self.db.flush()

    async def earnings(self, agent_id: uuid.UUID) -> tuple[int, int, list[DeliveryEarning]]:
        rows = list((await self.db.execute(
            select(DeliveryEarning).where(DeliveryEarning.agent_id == agent_id)
            .order_by(DeliveryEarning.created_at.desc())
        )).scalars().all())
        total = (await self.db.execute(
            select(func.coalesce(func.sum(DeliveryEarning.amount), 0)).where(DeliveryEarning.agent_id == agent_id)
        )).scalar_one()
        return int(total), len(rows), rows
