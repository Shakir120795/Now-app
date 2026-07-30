"""Order ORM models (map to db/schema.sql)."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, NUMERIC, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

order_status_enum = ENUM(
    "pending", "accepted", "preparing", "packed", "out_for_delivery",
    "delivered", "cancelled", "refunded", name="order_status", create_type=False,
)
payment_status_enum = ENUM(
    "pending", "authorized", "paid", "failed", "refunded", "partially_refunded",
    name="payment_status", create_type=False,
)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(order_status_enum, default="pending", nullable=False)
    payment_status: Mapped[str] = mapped_column(payment_status_enum, default="pending", nullable=False)

    ship_recipient: Mapped[str | None] = mapped_column(String(160))
    ship_phone: Mapped[str | None] = mapped_column(String(20))
    ship_line1: Mapped[str | None] = mapped_column(String(255))
    ship_line2: Mapped[str | None] = mapped_column(String(255))
    ship_landmark: Mapped[str | None] = mapped_column(String(160))
    ship_city: Mapped[str | None] = mapped_column(String(120))
    ship_state: Mapped[str | None] = mapped_column(String(120))
    ship_pincode: Mapped[str | None] = mapped_column(String(12))
    ship_lat: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 7))
    ship_lng: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 7))
    delivery_zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("delivery_zones.id"))

    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    subtotal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    membership_discount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tax_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shipping_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tip_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wallet_applied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grand_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("coupons.id"))

    is_gift: Mapped[bool] = mapped_column(default=False, nullable=False)
    gift_message: Mapped[str | None] = mapped_column(String(500))
    customer_notes: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    placed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items: Mapped[list["OrderItem"]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    history: Mapped[list["OrderStatusHistory"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id"))
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(160))
    unit_price_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[int] = mapped_column(Integer, nullable=False)

    addons: Mapped[list["OrderItemAddon"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class OrderItemAddon(Base):
    __tablename__ = "order_item_addons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    addon_name: Mapped[str] = mapped_column(String(120), nullable=False)
    price_amount: Mapped[int] = mapped_column(Integer, nullable=False)


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(order_status_enum)
    to_status: Mapped[str] = mapped_column(order_status_enum, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrderDelivery(Base):
    __tablename__ = "order_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("delivery_agents.id"))
    otp_hash: Mapped[str | None] = mapped_column(Text)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    picked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_lat: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 7))
    current_lng: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 7))
