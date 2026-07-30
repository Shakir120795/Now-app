"""Analytics + audit data access (SQL aggregates)."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analytics.models import AuditLog


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def dashboard(self, start: date, end: date) -> dict:
        row = (await self.db.execute(
            text(
                """
                SELECT
                  COALESCE(SUM(grand_total) FILTER (WHERE payment_status = 'paid'), 0) AS revenue,
                  COUNT(*)                                                            AS orders,
                  COUNT(*) FILTER (WHERE status = 'delivered')                        AS delivered,
                  COUNT(*) FILTER (WHERE status = 'cancelled')                        AS cancelled
                FROM orders
                WHERE created_at::date BETWEEN :s AND :e
                """
            ),
            {"s": start, "e": end},
        )).mappings().first()
        new_customers = (await self.db.execute(
            text("SELECT COUNT(*) FROM users WHERE is_guest = false AND created_at::date BETWEEN :s AND :e"),
            {"s": start, "e": end},
        )).scalar_one()
        return {**dict(row), "new_customers": int(new_customers)}

    async def sales_series(self, start: date, end: date) -> list[dict]:
        rows = (await self.db.execute(
            text(
                """
                SELECT created_at::date AS d,
                       COALESCE(SUM(grand_total) FILTER (WHERE payment_status = 'paid'), 0) AS revenue,
                       COUNT(*) AS orders
                FROM orders
                WHERE created_at::date BETWEEN :s AND :e
                GROUP BY created_at::date
                ORDER BY created_at::date
                """
            ),
            {"s": start, "e": end},
        )).mappings().all()
        return [dict(r) for r in rows]

    async def top_products(self, start: date, end: date, limit: int = 10) -> list[dict]:
        rows = (await self.db.execute(
            text(
                """
                SELECT oi.product_name,
                       SUM(oi.quantity)   AS units,
                       SUM(oi.line_total) AS revenue
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.payment_status = 'paid' AND o.created_at::date BETWEEN :s AND :e
                GROUP BY oi.product_name
                ORDER BY units DESC
                LIMIT :lim
                """
            ),
            {"s": start, "e": end, "lim": limit},
        )).mappings().all()
        return [dict(r) for r in rows]

    # ----- audit -----
    async def write_audit(self, log: AuditLog) -> None:
        self.db.add(log)
        await self.db.flush()

    async def list_audit(self, offset: int, limit: int) -> list[AuditLog]:
        res = await self.db.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        )
        return list(res.scalars().all())
