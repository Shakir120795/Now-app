"""Payments data access."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.payments.models import Payment, PaymentWebhook, SavedCard


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_payment(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def payment_by_provider_ref(self, provider_ref: str) -> Payment | None:
        res = await self.db.execute(select(Payment).where(Payment.provider_ref == provider_ref))
        return res.scalar_one_or_none()

    async def latest_for_order(self, order_id: uuid.UUID) -> Payment | None:
        res = await self.db.execute(
            select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at.desc()).limit(1)
        )
        return res.scalar_one_or_none()

    async def set_payment_status(self, payment: Payment, status: str, payload: dict | None = None) -> None:
        payment.status = status
        if payload is not None:
            payment.raw_payload = payload
        await self.db.flush()

    async def record_webhook(self, provider: str, event_id: str | None, valid: bool, payload: dict) -> tuple[PaymentWebhook, bool]:
        """Idempotent by (provider, event_id). Returns (row, already_seen)."""
        if event_id:
            res = await self.db.execute(
                select(PaymentWebhook).where(
                    PaymentWebhook.provider == provider, PaymentWebhook.event_id == event_id
                )
            )
            existing = res.scalar_one_or_none()
            if existing:
                return existing, True
        wh = PaymentWebhook(provider=provider, event_id=event_id, signature_valid=valid, payload=payload)
        self.db.add(wh)
        await self.db.flush()
        return wh, False

    async def mark_webhook_processed(self, wh: PaymentWebhook) -> None:
        wh.processed_at = datetime.now(timezone.utc)
        await self.db.flush()

    # ----- saved cards -----
    async def list_cards(self, user_id: uuid.UUID) -> list[SavedCard]:
        res = await self.db.execute(select(SavedCard).where(SavedCard.user_id == user_id))
        return list(res.scalars().all())

    async def add_card(self, card: SavedCard) -> SavedCard:
        self.db.add(card)
        await self.db.flush()
        return card

    async def delete_card(self, user_id: uuid.UUID, card_id: uuid.UUID) -> None:
        card = await self.db.get(SavedCard, card_id)
        if card and card.user_id == user_id:
            await self.db.delete(card)
            await self.db.flush()
