"""Wallet data access."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.wallet.models import Wallet, WalletTransaction


class WalletRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: uuid.UUID) -> Wallet:
        res = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = res.scalar_one_or_none()
        if wallet is None:
            wallet = Wallet(user_id=user_id, balance_amount=0)
            self.db.add(wallet)
            await self.db.flush()
        return wallet

    async def list_transactions(self, wallet_id: uuid.UUID, offset: int, limit: int) -> list[WalletTransaction]:
        res = await self.db.execute(
            select(WalletTransaction)
            .where(WalletTransaction.wallet_id == wallet_id)
            .order_by(WalletTransaction.created_at.desc())
            .offset(offset).limit(limit)
        )
        return list(res.scalars().all())

    async def adjust(self, wallet: Wallet, amount: int, note: str | None) -> WalletTransaction:
        """amount>0 credit, amount<0 debit. Guards against negative balance."""
        new_balance = wallet.balance_amount + amount
        if new_balance < 0:
            from app.core.errors import BadRequest
            raise BadRequest("Adjustment would make wallet balance negative.")
        wallet.balance_amount = new_balance
        txn = WalletTransaction(
            wallet_id=wallet.id,
            direction="credit" if amount > 0 else "debit",
            amount=abs(amount), balance_after=new_balance,
            source="admin", note=note,
        )
        self.db.add(txn)
        await self.db.flush()
        return txn
