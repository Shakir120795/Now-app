"""Delivery ORM models (DeliveryAgent, DeliveryEarning). OrderDelivery lives in orders."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

agent_status_enum = ENUM("available", "busy", "offline", name="agent_status", create_type=False)


class DeliveryAgent(Base):
    __tablename__ = "delivery_agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(agent_status_enum, default="offline", nullable=False)
    vehicle_type: Mapped[str | None] = mapped_column(String(40))
    current_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    current_lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    rating_avg: Mapped[float] = mapped_column(Numeric(3, 2), default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeliveryEarning(Base):
    __tablename__ = "delivery_earnings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("delivery_agents.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(24), default="delivery_fee", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
