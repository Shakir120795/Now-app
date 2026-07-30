"""Cart use-cases: mutate cart + build the authoritative pricing quote."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequest, NotFound
from app.features.auth.models import User
from app.features.cart.models import Cart
from app.features.cart.pricing import (
    CouponSpec,
    CouponType,
    LineItem,
    PricingInput,
    compute,
)
from app.features.cart.repository import CartRepository
from app.features.cart.schemas import (
    AddItemIn,
    CartItemAddonOut,
    CartItemOut,
    CartOut,
    PricingQuoteOut,
    QuoteRequest,
    UpdateItemIn,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CartService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CartRepository(db)

    # ---------------- mutations ----------------
    async def add_item(self, principal: dict, body: AddItemIn) -> CartOut:
        cart = await self.repo.get_or_create(principal["user_id"], principal["guest_token"])
        variant = await self.repo.get_variant(body.variant_id)
        if variant is None or not variant.is_active:
            raise NotFound("Product variant not available.")
        inv = variant.inventory
        if inv and inv.track and inv.available < body.quantity:
            raise BadRequest("Not enough stock for the requested quantity.")
        addons = await self.repo.get_addons(body.addon_ids)
        await self.repo.add_item(cart.id, variant, body.quantity, addons, body.notes)
        return await self._build(cart, QuoteRequest(), principal)

    async def update_item(self, principal: dict, item_id: uuid.UUID, body: UpdateItemIn) -> CartOut:
        cart = await self._require_cart(principal)
        item = await self.repo.get_item(cart.id, item_id)
        if item is None:
            raise NotFound("Cart item not found.")
        await self.repo.update_item(item, body.quantity, body.notes)
        return await self._build(cart, QuoteRequest(), principal)

    async def remove_item(self, principal: dict, item_id: uuid.UUID) -> CartOut:
        cart = await self._require_cart(principal)
        item = await self.repo.get_item(cart.id, item_id)
        if item is None:
            raise NotFound("Cart item not found.")
        await self.repo.remove_item(item)
        return await self._build(cart, QuoteRequest(), principal)

    # ---------------- read / quote ----------------
    async def get_cart(self, principal: dict, quote: QuoteRequest | None = None) -> CartOut:
        cart = await self.repo.active_cart(principal["user_id"], principal["guest_token"])
        if cart is None:
            cart = await self.repo.create_cart(principal["user_id"], principal["guest_token"])
        return await self._build(cart, quote or QuoteRequest(), principal)

    # ---------------- internal ----------------
    async def _require_cart(self, principal: dict) -> Cart:
        cart = await self.repo.active_cart(principal["user_id"], principal["guest_token"])
        if cart is None:
            raise NotFound("No active cart.")
        return cart

    async def _build(self, cart: Cart, quote: QuoteRequest, principal: dict) -> CartOut:
        await self.db.refresh(cart)
        line_items: list[LineItem] = []
        item_outs: list[CartItemOut] = []

        for item in cart.items:
            variant = await self.repo.get_variant(item.variant_id)
            product = await self.repo.get_product(variant.product_id) if variant else None
            tax_bps = await self.repo.get_tax_bps(product.tax_class_id) if product else 0
            addons_total = sum(a.price_amount for a in item.addons)
            line_items.append(LineItem(
                unit_price=item.unit_price_amount, quantity=item.quantity,
                addons_total=addons_total, tax_bps=tax_bps,
            ))
            item_outs.append(CartItemOut(
                id=item.id, variant_id=item.variant_id,
                product_name=product.name if product else None,
                variant_name=variant.name if variant else None,
                quantity=item.quantity, unit_price_amount=item.unit_price_amount,
                addons=[CartItemAddonOut(addon_id=a.addon_id, price_amount=a.price_amount) for a in item.addons],
                line_total=(item.unit_price_amount + addons_total) * item.quantity,
                notes=item.notes,
            ))

        coupon = await self._resolve_coupon(quote.coupon_code)
        benefits = await self.repo.active_membership_benefits(principal["user_id"])
        zone = await self.repo.delivery_zone_for_address(quote.address_id)
        wallet = await self.repo.wallet_balance(principal["user_id"])

        breakdown = compute(PricingInput(
            items=line_items,
            coupon=coupon,
            membership_discount_bps=int(benefits.get("discount_bps", 0)) if benefits else 0,
            membership_free_delivery=bool(benefits.get("free_delivery", False)) if benefits else False,
            base_shipping=int(zone.get("base_fee", 0) or 0),
            free_above=zone.get("free_above"),
            tip=quote.tip,
            wallet_balance=wallet,
            use_wallet=quote.use_wallet,
        ))

        return CartOut(
            id=cart.id, items=item_outs,
            quote=PricingQuoteOut(
                subtotal=breakdown.subtotal, discount_total=breakdown.discount_total,
                membership_discount=breakdown.membership_discount, tax_total=breakdown.tax_total,
                shipping_total=breakdown.shipping_total, tip_amount=breakdown.tip_amount,
                wallet_applied=breakdown.wallet_applied, grand_total=breakdown.grand_total,
                coupon_applied=breakdown.coupon_applied, coupon_error=breakdown.coupon_error,
            ),
        )

    async def _resolve_coupon(self, code: str | None) -> CouponSpec | None:
        if not code:
            return None
        row = await self.repo.get_coupon(code)
        if not row or not row["is_active"]:
            return None
        now = _now()
        if row["starts_at"] and row["starts_at"] > now:
            return None
        if row["ends_at"] and row["ends_at"] < now:
            return None
        return CouponSpec(
            type=CouponType(row["type"]),
            value=int(row["value"]),
            min_order=int(row["min_order"] or 0),
            max_discount=row["max_discount"],
        )
