"""Delivery agent use-cases: accept/reject, advance, OTP delivery, earnings."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequest, Forbidden, NotFound, Unauthorized
from app.features.auth.models import User
from app.features.delivery.models import DeliveryAgent, DeliveryEarning
from app.features.delivery.repository import DeliveryRepository
from app.features.delivery.schemas import (
    AssignmentOut,
    AvailabilityIn,
    EarningOut,
    EarningsSummaryOut,
)
from app.features.notifications.service import NotificationService
from app.features.orders.lifecycle import can_transition
from app.features.orders.repository import OrderRepository
from app.core.security import generate_otp, hash_secret, verify_secret


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DeliveryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DeliveryRepository(db)
        self.orders = OrderRepository(db)
        self.notifier = NotificationService(db)

    async def _require_agent(self, user: User) -> DeliveryAgent:
        agent = await self.repo.agent_by_user(user.id)
        if agent is None:
            raise Forbidden("Not a delivery agent.")
        return agent

    async def assignments(self, user: User) -> list[AssignmentOut]:
        agent = await self._require_agent(user)
        rows = await self.repo.assignments(agent.id)
        return [
            AssignmentOut(
                order_id=o.id, order_number=o.order_number, status=o.status,
                ship_line1=o.ship_line1, ship_city=o.ship_city, ship_pincode=o.ship_pincode,
                grand_total=o.grand_total, assigned=(d.agent_id == agent.id),
            )
            for o, d in rows
        ]

    async def accept(self, user: User, order_id: uuid.UUID) -> dict:
        agent = await self._require_agent(user)
        d = await self.repo.delivery_for_order(order_id)
        if d is None:
            raise NotFound("Delivery not found.")
        if d.agent_id and d.agent_id != agent.id:
            raise BadRequest("Order already assigned to another agent.")
        d.agent_id = agent.id
        d.accepted_at = _now()
        agent.status = "busy"
        await self.db.flush()
        return {"status": "accepted"}

    async def reject(self, user: User, order_id: uuid.UUID) -> dict:
        agent = await self._require_agent(user)
        d = await self.repo.delivery_for_order(order_id)
        if d is None:
            raise NotFound("Delivery not found.")
        if d.agent_id == agent.id:
            d.agent_id = None
            d.rejected_at = _now()
            agent.status = "available"
            await self.db.flush()
        return {"status": "rejected"}

    async def advance(self, user: User, order_id: uuid.UUID, to_status: str) -> dict:
        agent = await self._require_agent(user)
        order = await self.repo.order(order_id)
        d = await self.repo.delivery_for_order(order_id)
        if order is None or d is None:
            raise NotFound("Order not found.")
        if d.agent_id != agent.id:
            raise Forbidden("Order not assigned to you.")
        if not can_transition(order.status, to_status):
            raise BadRequest(f"Illegal transition {order.status} → {to_status}.")
        from_s = order.status
        await self.orders.set_status(order, to_status)
        await self.orders.add_history(order.id, from_s, to_status, "Updated by agent", user.id)

        if to_status == "out_for_delivery":
            otp = generate_otp(4)
            d.otp_hash = hash_secret(otp)
            d.picked_at = _now()
            await self.notifier.notify(
                order.user_id, "Your order is on the way",
                f"Share OTP {otp} with the delivery partner to receive your order.",
                data={"order_id": str(order.id), "type": "delivery_otp"},
            )
        await self.db.flush()
        return {"status": to_status}

    async def deliver(self, user: User, order_id: uuid.UUID, otp: str) -> dict:
        agent = await self._require_agent(user)
        order = await self.repo.order(order_id)
        d = await self.repo.delivery_for_order(order_id)
        if order is None or d is None:
            raise NotFound("Order not found.")
        if d.agent_id != agent.id:
            raise Forbidden("Order not assigned to you.")
        if not d.otp_hash or not verify_secret(otp, d.otp_hash):
            raise Unauthorized("Invalid delivery OTP.")
        from_s = order.status
        await self.orders.set_status(order, "delivered")
        await self.orders.add_history(order.id, from_s, "delivered", "Delivered (OTP verified)", user.id)
        d.delivered_at = _now()
        if order.payment_status != "paid":  # COD collected on delivery
            order.payment_status = "paid"
        # record earning (delivery fee + tip)
        await self.repo.add_earning(DeliveryEarning(
            agent_id=agent.id, order_id=order.id,
            amount=order.shipping_total + order.tip_amount, type="delivery_fee",
        ))
        agent.status = "available"
        await self.notifier.notify(order.user_id, "Order delivered", "Your order has been delivered. Enjoy!",
                                   data={"order_id": str(order.id)})
        await self.db.flush()
        return {"status": "delivered"}

    async def set_availability(self, user: User, body: AvailabilityIn) -> dict:
        agent = await self._require_agent(user)
        agent.status = body.status
        if body.lat is not None:
            agent.current_lat = body.lat
        if body.lng is not None:
            agent.current_lng = body.lng
        await self.db.flush()
        return {"status": agent.status}

    async def earnings(self, user: User) -> EarningsSummaryOut:
        agent = await self._require_agent(user)
        total, count, rows = await self.repo.earnings(agent.id)
        return EarningsSummaryOut(
            total=total, count=count,
            earnings=[EarningOut(id=e.id, order_id=e.order_id, amount=e.amount,
                                 type=e.type, created_at=e.created_at) for e in rows],
        )
