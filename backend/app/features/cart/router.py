"""Cart transport. Works for both registered customers and guests.

Principal resolution: a registered user (if a valid access token is present) else a
guest cart keyed by the `X-Guest-Token` header.
"""
from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.features.cart.schemas import (
    AddItemIn,
    ApplyCouponIn,
    CartOut,
    QuoteRequest,
    UpdateItemIn,
)
from app.features.cart.service import CartService

router = APIRouter(prefix="/cart", tags=["cart"])


def _principal(request: Request, x_guest_token: str | None) -> dict:
    """Extract (user_id | guest_token). Registered users take precedence."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = decode_token(auth.removeprefix("Bearer ").strip())
            if payload.get("type") == "access" and not payload.get("guest", False):
                return {"user_id": uuid.UUID(payload["sub"]), "guest_token": None}
        except jwt.PyJWTError:
            pass
    return {"user_id": None, "guest_token": x_guest_token}


@router.get("", response_model=CartOut)
async def get_cart(
    request: Request,
    x_guest_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await CartService(db).get_cart(_principal(request, x_guest_token))


@router.post("/items", response_model=CartOut)
async def add_item(
    body: AddItemIn, request: Request,
    x_guest_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await CartService(db).add_item(_principal(request, x_guest_token), body)


@router.patch("/items/{item_id}", response_model=CartOut)
async def update_item(
    item_id: uuid.UUID, body: UpdateItemIn, request: Request,
    x_guest_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await CartService(db).update_item(_principal(request, x_guest_token), item_id, body)


@router.delete("/items/{item_id}", response_model=CartOut)
async def remove_item(
    item_id: uuid.UUID, request: Request,
    x_guest_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await CartService(db).remove_item(_principal(request, x_guest_token), item_id)


@router.post("/quote", response_model=CartOut)
async def quote(
    body: QuoteRequest, request: Request,
    x_guest_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await CartService(db).get_cart(_principal(request, x_guest_token), body)


@router.post("/coupon", response_model=CartOut)
async def apply_coupon(
    body: ApplyCouponIn, request: Request,
    x_guest_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await CartService(db).get_cart(
        _principal(request, x_guest_token), QuoteRequest(coupon_code=body.code)
    )
