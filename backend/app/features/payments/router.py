"""Payments transport: intents, verify, webhooks (signed), saved cards."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_customer
from app.db.session import get_db
from app.features.auth.models import User
from app.features.payments.schemas import (
    IntentOut,
    SavedCardIn,
    SavedCardOut,
    VerifyIn,
    VerifyOut,
)
from app.features.payments.service import PaymentService

router = APIRouter(tags=["payments"])


@router.post("/payments/{order_id}/intent", response_model=IntentOut)
async def create_intent(
    order_id: uuid.UUID, provider: str,
    user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db),
):
    return await PaymentService(db).create_intent(user, order_id, provider)


@router.post("/payments/verify", response_model=VerifyOut)
async def verify_payment(
    body: VerifyIn, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db),
):
    return await PaymentService(db).verify(user, body.order_id, body.provider, body.payload, body.signature)


@router.post("/payments/webhook/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    raw = await request.body()
    parsed = json.loads(raw or b"{}")
    return await PaymentService(db).handle_webhook("razorpay", raw, x_razorpay_signature or "", parsed)


@router.post("/payments/webhook/phonepe", status_code=status.HTTP_200_OK)
async def phonepe_webhook(
    request: Request,
    x_verify: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    raw = await request.body()
    parsed = json.loads(raw or b"{}")
    return await PaymentService(db).handle_webhook("phonepe", raw, x_verify or "", parsed)


# ----- saved cards -----
@router.get("/me/cards", response_model=list[SavedCardOut], tags=["cards"])
async def list_cards(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await PaymentService(db).list_cards(user)


@router.post("/me/cards", response_model=SavedCardOut, status_code=201, tags=["cards"])
async def add_card(body: SavedCardIn, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await PaymentService(db).add_card(user, body)


@router.delete("/me/cards/{card_id}", status_code=204, tags=["cards"])
async def delete_card(card_id: uuid.UUID, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    await PaymentService(db).delete_card(user, card_id)
