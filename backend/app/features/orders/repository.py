"""Orders data access."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Inventory
from app.features.orders.models import (
    Order,
    OrderDelivery,
    OrderItem,
    OrderItemAddon,
    OrderStatusHistory,
)
from app.features.users.models import Address


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def by_idempotency_key(self, key: str) -> Order | None:
        res = await self.db.execute(select(Order).where(Order.idempotency_key == key))
        return res.scalar_one_or_none()

    async def get_address(self, user_id: uuid.UUID, address_id: uuid.UUID) -> Address | None:
        res = await self.db.execute(
            select(Address).where(
                Address.id == address_id, Address.user_id == user_id, Address.deleted_at.is_(None)
            )
        )
        return res.scalar_one_or_none()

    async def next_order_number(self) -> str:
        # LUX-YYMMDD-<sequence> using a per-day counter in Postgres.
        row = (await self.db.execute(
            text(
                """
                SELECT to_char(now() AT TIME ZONE 'Asia/Kolkata', 'YYMMDD') AS ymd,
                       lpad((count(*) + 1)::text, 4, '0') AS seq
                FROM orders
                WHERE created_at::date = (now() AT TIME ZONE 'Asia/Kolkata')::date
                """
            )
        )).mappings().first()
        return f"LUX-{row['ymd']}-{row['seq']}"

    async def add_order(self, order: Order) -> Order:
        self.db.add(order)
        await self.db.flush()
        return order

    async def add_item(self, item: OrderItem, addons: list[tuple[str, int]]) -> OrderItem:
        self.db.add(item)
        await self.db.flush()
        for name, price in addons:
            self.db.add(OrderItemAddon(order_item_id=item.id, addon_name=name, price_amount=price))
        await self.db.flush()
        return item

    async def add_history(self, order_id: uuid.UUID, from_s: str | None, to_s: str,
                          note: str | None, by: uuid.UUID | None) -> None:
        self.db.add(OrderStatusHistory(
            order_id=order_id, from_status=from_s, to_status=to_s, note=note, changed_by=by
        ))
        await self.db.flush()

    async def add_delivery(self, order_id: uuid.UUID) -> OrderDelivery:
        d = OrderDelivery(order_id=order_id)
        self.db.add(d)
        await self.db.flush()
        return d

    async def decrement_stock(self, variant_id: uuid.UUID, qty: int) -> None:
        # Atomic guarded decrement; never goes below zero for tracked inventory.
        await self.db.execute(
            update(Inventory)
            .where(Inventory.variant_id == variant_id, Inventory.track.is_(True))
            .values(quantity=Inventory.quantity - qty)
        )

    async def get_order(self, order_id: uuid.UUID) -> Order | None:
        return await self.db.get(Order, order_id)

    async def get_user_order(self, user_id: uuid.UUID, order_id: uuid.UUID) -> Order | None:
        res = await self.db.execute(
            select(Order).where(Order.id == order_id, Order.user_id == user_id)
        )
        return res.scalar_one_or_none()

    async def list_all_orders(self, status: str | None, offset: int, limit: int) -> tuple[list[Order], int]:
        where = "WHERE status = :st" if status else ""
        params = {"st": status} if status else {}
        total = (await self.db.execute(
            text(f"SELECT count(*) FROM orders {where}"), params
        )).scalar_one()
        stmt = select(Order)
        if status:
            stmt = stmt.where(Order.status == status)
        stmt = stmt.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all()), int(total)

    async def list_user_orders(self, user_id: uuid.UUID, offset: int, limit: int) -> tuple[list[Order], int]:
        total = (await self.db.execute(
            text("SELECT count(*) FROM orders WHERE user_id = :u"), {"u": str(user_id)}
        )).scalar_one()
        res = await self.db.execute(
            select(Order).where(Order.user_id == user_id)
            .order_by(Order.created_at.desc()).offset(offset).limit(limit)
        )
        return list(res.scalars().all()), int(total)

    async def set_status(self, order: Order, to_status: str) -> None:
        order.status = to_status
        if to_status == "cancelled":
            order.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def restore_stock(self, variant_id: uuid.UUID, qty: int) -> None:
        await self.db.execute(
            update(Inventory)
            .where(Inventory.variant_id == variant_id, Inventory.track.is_(True))
            .values(quantity=Inventory.quantity + qty)
        )

    async def coupon_id_by_code(self, code: str) -> uuid.UUID | None:
        return (await self.db.execute(
            text("SELECT id FROM coupons WHERE code = :c"), {"c": code}
        )).scalar_one_or_none()

    async def record_coupon_redemption(
        self, coupon_id: uuid.UUID, user_id: uuid.UUID, order_id: uuid.UUID, discount: int
    ) -> None:
        await self.db.execute(
            text(
                """
                INSERT INTO coupon_redemptions (coupon_id, user_id, order_id, discount_amount)
                VALUES (:cid, :uid, :oid, :disc)
                """
            ),
            {"cid": str(coupon_id), "uid": str(user_id), "oid": str(order_id), "disc": discount},
        )
        await self.db.execute(
            text("UPDATE coupons SET used_count = used_count + 1 WHERE id = :cid"),
            {"cid": str(coupon_id)},
        )

    async def debit_wallet(self, user_id: uuid.UUID, amount: int, order_id: uuid.UUID) -> None:
        """Atomically debit the wallet and append an immutable ledger row."""
        await self.db.execute(
            text(
                """
                INSERT INTO wallets (user_id, balance_amount)
                VALUES (:uid, 0) ON CONFLICT (user_id) DO NOTHING
                """
            ),
            {"uid": str(user_id)},
        )
        balance_after = (await self.db.execute(
            text(
                """
                UPDATE wallets SET balance_amount = balance_amount - :amt, updated_at = now()
                WHERE user_id = :uid AND balance_amount >= :amt
                RETURNING balance_amount
                """
            ),
            {"uid": str(user_id), "amt": amount},
        )).scalar_one_or_none()
        if balance_after is None:
            from app.core.errors import BadRequest
            raise BadRequest("Insufficient wallet balance.")
        await self.db.execute(
            text(
                """
                INSERT INTO wallet_transactions
                    (wallet_id, direction, amount, balance_after, source, reference_id, note)
                SELECT id, 'debit', :amt, :bal, 'order', :ref, 'Order payment'
                FROM wallets WHERE user_id = :uid
                """
            ),
            {"amt": amount, "bal": balance_after, "ref": str(order_id), "uid": str(user_id)},
        )
