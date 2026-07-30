"""Payments use-cases: intent creation, client verify, webhook processing."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequest, NotFound, Unauthorized
from app.features.auth.models import User
from app.features.orders.repository import OrderRepository
from app.features.payments.gateways.base import PaymentGateway
from app.features.payments.gateways.phonepe_gw import PhonePeGateway
from app.features.payments.gateways.razorpay_gw import RazorpayGateway
from app.features.payments.models import Payment, SavedCard
from app.features.payments.repository import PaymentRepository
from app.features.payments.schemas import IntentOut, SavedCardIn, SavedCardOut, VerifyOut

_GATEWAYS: dict[str, PaymentGateway] = {
    "razorpay": RazorpayGateway(),
    "phonepe": PhonePeGateway(),
}


def _gateway(provider: str) -> PaymentGateway:
    gw = _GATEWAYS.get(provider)
    if gw is None:
        raise BadRequest(f"Unsupported payment provider: {provider}")
    return gw


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PaymentRepository(db)
        self.orders = OrderRepository(db)

    async def create_intent(self, user: User, order_id: uuid.UUID, provider: str) -> IntentOut:
        order = await self.orders.get_user_order(user.id, order_id)
        if order is None:
            raise NotFound("Order not found.")
        if order.grand_total <= 0:
            raise BadRequest("Order is already fully paid.")
        if order.payment_status == "paid":
            raise BadRequest("Order is already paid.")

        gw = _gateway(provider)
        result = await gw.create_intent(
            order_number=order.order_number, amount=order.grand_total, currency=order.currency
        )
        await self.repo.create_payment(Payment(
            order_id=order.id, provider=provider, method=provider,
            provider_ref=result.provider_ref, amount=result.amount, currency=result.currency,
            status="pending",
        ))
        return IntentOut(
            provider=result.provider, provider_ref=result.provider_ref,
            amount=result.amount, currency=result.currency, extra=result.extra,
        )

    async def verify(self, user: User, order_id: uuid.UUID, provider: str, payload: dict, signature: str | None) -> VerifyOut:
        order = await self.orders.get_user_order(user.id, order_id)
        if order is None:
            raise NotFound("Order not found.")
        gw = _gateway(provider)
        ok = gw.verify_callback(payload, raw_body=b"", signature=signature or "")
        if not ok:
            raise Unauthorized("Payment signature verification failed.")
        await self._mark_paid(order_id, payload)
        await self.db.refresh(order)
        return VerifyOut(order_id=order.id, payment_status=order.payment_status, order_status=order.status)

    async def handle_webhook(self, provider: str, raw_body: bytes, signature: str, parsed: dict) -> dict:
        gw = _gateway(provider)
        valid = gw.verify_callback(parsed, raw_body=raw_body, signature=signature)
        event_id = parsed.get("id") or parsed.get("event_id") or parsed.get("merchantTransactionId")
        wh, already = await self.repo.record_webhook(provider, event_id, valid, parsed)
        if already:
            return {"status": "duplicate_ignored"}
        if not valid:
            return {"status": "invalid_signature"}

        # Resolve the order via provider_ref on the payment record.
        provider_ref = (
            parsed.get("razorpay_order_id")
            or parsed.get("merchantTransactionId")
            or parsed.get("order_id")
        )
        if provider_ref:
            payment = await self.repo.payment_by_provider_ref(provider_ref)
            if payment:
                await self._mark_paid(payment.order_id, parsed, payment=payment)
        await self.repo.mark_webhook_processed(wh)
        return {"status": "processed"}

    async def _mark_paid(self, order_id: uuid.UUID, payload: dict, payment: Payment | None = None) -> None:
        order = await self.orders.get_order(order_id)
        if order is None:
            return
        if payment is None:
            payment = await self.repo.latest_for_order(order_id)
        if payment:
            await self.repo.set_payment_status(payment, "paid", payload)
        if order.payment_status != "paid":
            order.payment_status = "paid"
            if order.status == "pending":
                from_s = order.status
                await self.orders.set_status(order, "accepted")
                await self.orders.add_history(order.id, from_s, "accepted", "Payment received", None)
        await self.db.flush()

    # ----- saved cards -----
    async def list_cards(self, user: User) -> list[SavedCardOut]:
        cards = await self.repo.list_cards(user.id)
        return [SavedCardOut(
            id=c.id, provider=c.provider, brand=c.brand, last4=c.last4,
            exp_month=c.exp_month, exp_year=c.exp_year, is_default=c.is_default,
        ) for c in cards]

    async def add_card(self, user: User, body: SavedCardIn) -> SavedCardOut:
        c = await self.repo.add_card(SavedCard(user_id=user.id, **body.model_dump()))
        return SavedCardOut(
            id=c.id, provider=c.provider, brand=c.brand, last4=c.last4,
            exp_month=c.exp_month, exp_year=c.exp_year, is_default=c.is_default,
        )

    async def delete_card(self, user: User, card_id: uuid.UUID) -> None:
        await self.repo.delete_card(user.id, card_id)
