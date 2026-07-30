"""Delivery agent transport."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.features.auth.models import User
from app.features.delivery.schemas import (
    AdvanceStatusIn,
    AssignmentOut,
    AvailabilityIn,
    DeliverIn,
    EarningsSummaryOut,
)
from app.features.delivery.service import DeliveryService

router = APIRouter(prefix="/agent", tags=["delivery"])


@router.get("/assignments", response_model=list[AssignmentOut])
async def assignments(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DeliveryService(db).assignments(user)


@router.post("/assignments/{order_id}/accept")
async def accept(order_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DeliveryService(db).accept(user, order_id)


@router.post("/assignments/{order_id}/reject")
async def reject(order_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DeliveryService(db).reject(user, order_id)


@router.post("/orders/{order_id}/status")
async def advance(order_id: uuid.UUID, body: AdvanceStatusIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DeliveryService(db).advance(user, order_id, body.to_status)


@router.post("/orders/{order_id}/deliver")
async def deliver(order_id: uuid.UUID, body: DeliverIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DeliveryService(db).deliver(user, order_id, body.otp)


@router.patch("/availability")
async def availability(body: AvailabilityIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DeliveryService(db).set_availability(user, body)


@router.get("/earnings", response_model=EarningsSummaryOut)
async def earnings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DeliveryService(db).earnings(user)
