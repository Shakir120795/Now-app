"""Orders transport: customer checkout + reads; admin status transitions."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_customer, require_permission
from app.core.pagination import Page, PageParams
from app.db.session import get_db
from app.features.auth.models import User
from app.features.orders.schemas import (
    OrderCard,
    OrderOut,
    PlaceOrderIn,
    PlaceOrderOut,
    StatusUpdateIn,
)
from fastapi import Query
from app.features.orders.service import OrderService

router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=PlaceOrderOut, status_code=201)
async def place_order(
    body: PlaceOrderIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService(db).place_order(user, body, idempotency_key)


@router.get("/orders", response_model=Page[OrderCard])
async def list_orders(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db),
):
    return await OrderService(db).list_orders(user, PageParams(page=page, page_size=page_size))


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(order_id: uuid.UUID, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await OrderService(db).get_order(user, order_id)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(order_id: uuid.UUID, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await OrderService(db).cancel(user, order_id)


# ---------------- admin ----------------
admin_router = APIRouter(prefix="/admin", tags=["admin:orders"])


@admin_router.get("/orders", response_model=Page[OrderCard])
async def admin_list_orders(
    status: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_permission("order.read")),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService(db).admin_list_orders(status, PageParams(page=page, page_size=page_size))


@admin_router.patch("/orders/{order_id}/status", response_model=OrderOut)
async def update_status(
    order_id: uuid.UUID, body: StatusUpdateIn,
    actor: User = Depends(require_permission("order.update")),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService(db).admin_transition(order_id, body.to_status, body.note, actor)
