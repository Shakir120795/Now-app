"""Wallet transport."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_customer, require_permission
from app.core.pagination import Page, PageParams
from app.db.session import get_db
from app.features.auth.models import User
from app.features.wallet.schemas import AdjustIn, TxnOut, WalletOut
from app.features.wallet.service import WalletService

router = APIRouter(tags=["wallet"])


@router.get("/me/wallet", response_model=WalletOut)
async def my_wallet(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await WalletService(db).get_wallet(user)


@router.get("/me/wallet/transactions", response_model=Page[TxnOut])
async def my_transactions(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db),
):
    return await WalletService(db).transactions(user, PageParams(page=page, page_size=page_size))


admin_router = APIRouter(prefix="/admin", tags=["admin:wallet"])


@admin_router.post("/users/{user_id}/wallet/adjust", response_model=WalletOut)
async def adjust_wallet(
    user_id: uuid.UUID, body: AdjustIn,
    _: User = Depends(require_permission("wallet.adjust")), db: AsyncSession = Depends(get_db),
):
    return await WalletService(db).admin_adjust(user_id, body.amount, body.note)
