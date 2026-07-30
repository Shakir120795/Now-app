"""Wallet use-cases."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequest
from app.core.pagination import Page, PageParams, build_page
from app.features.auth.models import User
from app.features.wallet.repository import WalletRepository
from app.features.wallet.schemas import TxnOut, WalletOut


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WalletRepository(db)

    async def get_wallet(self, user: User) -> WalletOut:
        w = await self.repo.get_or_create(user.id)
        return WalletOut(balance_amount=w.balance_amount, currency=w.currency)

    async def transactions(self, user: User, params: PageParams) -> Page[TxnOut]:
        w = await self.repo.get_or_create(user.id)
        txns = await self.repo.list_transactions(w.id, params.offset, params.limit)
        items = [TxnOut(
            id=t.id, direction=t.direction, amount=t.amount, balance_after=t.balance_after,
            source=t.source, note=t.note, created_at=t.created_at,
        ) for t in txns]
        # total omitted for ledger view; use returned length-aware meta
        return build_page(items, len(items) + params.offset, params)

    async def admin_adjust(self, user_id: uuid.UUID, amount: int, note: str | None) -> WalletOut:
        if amount == 0:
            raise BadRequest("Amount must be non-zero.")
        w = await self.repo.get_or_create(user_id)
        await self.repo.adjust(w, amount, note)
        return WalletOut(balance_amount=w.balance_amount, currency=w.currency)
