"""Checkout & order lifecycle use-cases."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequest, Conflict, Forbidden, NotFound
from app.core.pagination import Page, PageParams, build_page
from app.features.auth.models import User
from app.features.cart.repository import CartRepository
from app.features.cart.schemas import QuoteRequest
from app.features.cart.service import CartService
from app.features.orders.lifecycle import CUSTOMER_CANCELLABLE, can_transition
from app.features.orders.models import Order, OrderItem
from app.features.orders.repository import OrderRepository
from app.features.orders.schemas import (
    OrderCard,
    OrderItemOut,
    OrderOut,
    PlaceOrderIn,
    PlaceOrderOut,
    StatusEvent,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id, order_number=order.order_number, status=order.status,
        payment_status=order.payment_status, currency=order.currency,
        subtotal=order.subtotal, discount_total=order.discount_total,
        membership_discount=order.membership_discount, tax_total=order.tax_total,
        shipping_total=order.shipping_total, tip_amount=order.tip_amount,
        wallet_applied=order.wallet_applied, grand_total=order.grand_total,
        items=[
            OrderItemOut(
                product_name=i.product_name, variant_name=i.variant_name,
                unit_price_amount=i.unit_price_amount, quantity=i.quantity,
                line_total=i.line_total,
                addons=[{"name": a.addon_name, "price": a.price_amount} for a in i.addons],
            )
            for i in order.items
        ],
        timeline=[
            StatusEvent(to_status=h.to_status, note=h.note, at=h.created_at)
            for h in sorted(order.history, key=lambda h: h.created_at)
        ],
        created_at=order.created_at,
    )


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrderRepository(db)
        self.cart_repo = CartRepository(db)

    # ---------------- checkout ----------------
    async def place_order(self, user: User, body: PlaceOrderIn, idempotency_key: str | None) -> PlaceOrderOut:
        if idempotency_key:
            existing = await self.repo.by_idempotency_key(idempotency_key)
            if existing:
                await self.db.refresh(existing)
                return self._result(existing, body.payment_method)

        address = await self.repo.get_address(user.id, body.address_id)
        if address is None:
            raise NotFound("Delivery address not found.")

        principal = {"user_id": user.id, "guest_token": None}
        cart_out = await CartService(self.db).get_cart(principal, QuoteRequest(
            coupon_code=body.coupon_code, use_wallet=body.use_wallet,
            tip=body.tip, address_id=body.address_id,
        ))
        if not cart_out.items:
            raise BadRequest("Cart is empty.")
        if body.coupon_code and cart_out.quote.coupon_error:
            raise BadRequest(f"Coupon not applicable: {cart_out.quote.coupon_error}")

        q = cart_out.quote
        cart = await self.cart_repo.active_cart(user.id, None)

        order = Order(
            order_number=await self.repo.next_order_number(),
            user_id=user.id,
            ship_recipient=address.recipient_name, ship_phone=address.phone,
            ship_line1=address.line1, ship_line2=address.line2, ship_landmark=address.landmark,
            ship_city=address.city, ship_state=address.state, ship_pincode=address.pincode,
            ship_lat=address.lat, ship_lng=address.lng,
            currency=q.currency, subtotal=q.subtotal, discount_total=q.discount_total,
            membership_discount=q.membership_discount, tax_total=q.tax_total,
            shipping_total=q.shipping_total, tip_amount=q.tip_amount,
            wallet_applied=q.wallet_applied, grand_total=q.grand_total,
            is_gift=body.is_gift, gift_message=body.gift_message, customer_notes=body.customer_notes,
            idempotency_key=idempotency_key, placed_at=_now(),
        )
        if body.coupon_code and q.coupon_applied:
            order.coupon_id = await self.repo.coupon_id_by_code(body.coupon_code)

        try:
            await self.repo.add_order(order)
        except Exception as exc:  # unique idempotency key race
            if idempotency_key:
                existing = await self.repo.by_idempotency_key(idempotency_key)
                if existing:
                    await self.db.refresh(existing)
                    return self._result(existing, body.payment_method)
            raise Conflict("Could not create order.") from exc

        # snapshot items + decrement stock
        addon_names = await self._addon_name_map(cart_out)
        for it in cart_out.items:
            oi = OrderItem(
                order_id=order.id, variant_id=it.variant_id,
                product_name=it.product_name or "Item", variant_name=it.variant_name,
                unit_price_amount=it.unit_price_amount, quantity=it.quantity,
                line_total=it.line_total,
            )
            addons = [(addon_names.get(a.addon_id, "Addon"), a.price_amount) for a in it.addons]
            await self.repo.add_item(oi, addons)
            await self.repo.decrement_stock(it.variant_id, it.quantity)

        # wallet debit (transactional with the order)
        if q.wallet_applied > 0:
            await self.repo.debit_wallet(user.id, q.wallet_applied, order.id)
        # coupon redemption
        if order.coupon_id:
            await self.repo.record_coupon_redemption(order.coupon_id, user.id, order.id, q.discount_total)

        # payment + status resolution
        remaining = q.grand_total
        requires_action = False
        if remaining == 0:
            order.payment_status = "paid"
            target = "accepted"
        elif body.payment_method == "cod":
            order.payment_status = "pending"
            target = "accepted"
        else:  # online gateway
            order.payment_status = "pending"
            target = "pending"
            requires_action = True

        await self.repo.add_history(order.id, None, "pending", "Order placed", user.id)
        if target != "pending":
            await self.repo.set_status(order, target)
            await self.repo.add_history(order.id, "pending", target, "Auto-accepted", None)

        await self.repo.add_delivery(order.id)
        if cart:
            await self.cart_repo.mark_ordered(cart)

        await self.db.flush()
        await self.db.refresh(order)
        return self._result(order, body.payment_method, requires_action)

    def _result(self, order: Order, method: str, requires_action: bool = False) -> PlaceOrderOut:
        return PlaceOrderOut(
            order=_order_out(order),
            payment={
                "provider": method,
                "method": method,
                "amount": order.grand_total,
                "requires_action": requires_action and order.payment_status != "paid",
            },
        )

    async def _addon_name_map(self, cart_out) -> dict[uuid.UUID, str]:
        ids = [a.addon_id for it in cart_out.items for a in it.addons]
        addons = await self.cart_repo.get_addons(ids)
        return {a.id: a.name for a in addons}

    # ---------------- reads ----------------
    async def list_orders(self, user: User, params: PageParams) -> Page[OrderCard]:
        orders, total = await self.repo.list_user_orders(user.id, params.offset, params.limit)
        cards = [
            OrderCard(id=o.id, order_number=o.order_number, status=o.status,
                      grand_total=o.grand_total, created_at=o.created_at)
            for o in orders
        ]
        return build_page(cards, total, params)

    async def admin_list_orders(self, status: str | None, params: PageParams) -> Page[OrderCard]:
        orders, total = await self.repo.list_all_orders(status, params.offset, params.limit)
        cards = [
            OrderCard(id=o.id, order_number=o.order_number, status=o.status,
                      grand_total=o.grand_total, created_at=o.created_at)
            for o in orders
        ]
        return build_page(cards, total, params)

    async def get_order(self, user: User, order_id: uuid.UUID) -> OrderOut:
        order = await self.repo.get_user_order(user.id, order_id)
        if order is None:
            raise NotFound("Order not found.")
        return _order_out(order)

    # ---------------- transitions ----------------
    async def cancel(self, user: User, order_id: uuid.UUID) -> OrderOut:
        order = await self.repo.get_user_order(user.id, order_id)
        if order is None:
            raise NotFound("Order not found.")
        if order.status not in CUSTOMER_CANCELLABLE:
            raise BadRequest(f"Order cannot be cancelled once it is '{order.status}'.")
        from_s = order.status
        await self.repo.set_status(order, "cancelled")
        await self.repo.add_history(order.id, from_s, "cancelled", "Cancelled by customer", user.id)
        for it in order.items:
            if it.variant_id:
                await self.repo.restore_stock(it.variant_id, it.quantity)
        await self.db.flush()
        await self.db.refresh(order)
        return _order_out(order)

    async def admin_transition(self, order_id: uuid.UUID, to_status: str, note: str | None, actor: User) -> OrderOut:
        order = await self.repo.get_order(order_id)
        if order is None:
            raise NotFound("Order not found.")
        if not can_transition(order.status, to_status):
            raise BadRequest(f"Illegal transition {order.status} → {to_status}.")
        from_s = order.status
        await self.repo.set_status(order, to_status)
        await self.repo.add_history(order.id, from_s, to_status, note, actor.id)
        await self.db.flush()
        await self.db.refresh(order)
        return _order_out(order)
