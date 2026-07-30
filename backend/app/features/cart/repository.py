"""Cart data access + pricing lookups (variants, addons, coupon, membership, zone, wallet)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.cart.models import Cart, CartItem, CartItemAddon
from app.features.catalog.models import Addon, Product, ProductVariant, TaxClass


class CartRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- cart lifecycle ----------
    async def active_cart(self, user_id: uuid.UUID | None, guest_token: str | None) -> Cart | None:
        stmt = select(Cart).where(Cart.status == "active")
        if user_id:
            stmt = stmt.where(Cart.user_id == user_id)
        else:
            stmt = stmt.where(Cart.guest_token == guest_token)
        return (await self.db.execute(stmt.limit(1))).scalar_one_or_none()

    async def create_cart(self, user_id: uuid.UUID | None, guest_token: str | None) -> Cart:
        cart = Cart(user_id=user_id, guest_token=guest_token, status="active")
        self.db.add(cart)
        await self.db.flush()
        return cart

    async def get_or_create(self, user_id: uuid.UUID | None, guest_token: str | None) -> Cart:
        cart = await self.active_cart(user_id, guest_token)
        return cart or await self.create_cart(user_id, guest_token)

    async def get_item(self, cart_id: uuid.UUID, item_id: uuid.UUID) -> CartItem | None:
        res = await self.db.execute(
            select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart_id)
        )
        return res.scalar_one_or_none()

    async def add_item(
        self, cart_id: uuid.UUID, variant: ProductVariant, quantity: int,
        addons: list[Addon], notes: str | None,
    ) -> CartItem:
        item = CartItem(
            cart_id=cart_id, variant_id=variant.id, quantity=quantity,
            unit_price_amount=variant.price_amount, notes=notes,
        )
        self.db.add(item)
        await self.db.flush()
        for a in addons:
            self.db.add(CartItemAddon(cart_item_id=item.id, addon_id=a.id, price_amount=a.price_amount))
        await self.db.flush()
        return item

    async def update_item(self, item: CartItem, quantity: int, notes: str | None) -> CartItem:
        item.quantity = quantity
        item.notes = notes
        await self.db.flush()
        return item

    async def remove_item(self, item: CartItem) -> None:
        await self.db.delete(item)
        await self.db.flush()

    async def mark_ordered(self, cart: Cart) -> None:
        cart.status = "ordered"
        await self.db.flush()

    # ---------- pricing lookups ----------
    async def get_variant(self, variant_id: uuid.UUID) -> ProductVariant | None:
        return await self.db.get(ProductVariant, variant_id)

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        return await self.db.get(Product, product_id)

    async def get_addons(self, addon_ids: list[uuid.UUID]) -> list[Addon]:
        if not addon_ids:
            return []
        res = await self.db.execute(select(Addon).where(Addon.id.in_(addon_ids)))
        return list(res.scalars().all())

    async def get_tax_bps(self, tax_class_id: uuid.UUID | None) -> int:
        if tax_class_id is None:
            return 0
        tc = await self.db.get(TaxClass, tax_class_id)
        return tc.rate_bps if tc else 0

    async def get_coupon(self, code: str) -> dict | None:
        row = (await self.db.execute(
            text(
                """
                SELECT type::text AS type, value, min_order, max_discount, is_active,
                       starts_at, ends_at
                FROM coupons WHERE code = :code
                """
            ),
            {"code": code},
        )).mappings().first()
        return dict(row) if row else None

    async def active_membership_benefits(self, user_id: uuid.UUID | None) -> dict:
        if not user_id:
            return {}
        row = (await self.db.execute(
            text(
                """
                SELECT p.benefits
                FROM memberships m JOIN membership_plans p ON p.id = m.plan_id
                WHERE m.user_id = :uid AND m.status = 'active'
                  AND (m.ends_at IS NULL OR m.ends_at > now())
                ORDER BY m.ends_at DESC NULLS LAST LIMIT 1
                """
            ),
            {"uid": str(user_id)},
        )).scalar_one_or_none()
        return row or {}

    async def delivery_zone_for_address(self, address_id: uuid.UUID | None) -> dict:
        # Resolve zone by the address pincode; fall back to the default zone.
        if address_id is not None:
            row = (await self.db.execute(
                text(
                    """
                    SELECT z.base_fee, z.free_above
                    FROM addresses a
                    JOIN delivery_zones z ON a.pincode = ANY(z.pincodes) AND z.is_active
                    WHERE a.id = :aid LIMIT 1
                    """
                ),
                {"aid": str(address_id)},
            )).mappings().first()
            if row:
                return dict(row)
        row = (await self.db.execute(
            text("SELECT base_fee, free_above FROM delivery_zones WHERE is_active ORDER BY name LIMIT 1")
        )).mappings().first()
        return dict(row) if row else {"base_fee": 0, "free_above": None}

    async def wallet_balance(self, user_id: uuid.UUID | None) -> int:
        if not user_id:
            return 0
        bal = (await self.db.execute(
            text("SELECT balance_amount FROM wallets WHERE user_id = :uid"),
            {"uid": str(user_id)},
        )).scalar_one_or_none()
        return int(bal or 0)
