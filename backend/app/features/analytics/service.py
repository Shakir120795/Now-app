"""Analytics + audit use-cases."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page, PageParams, build_page
from app.features.analytics.models import AuditLog
from app.features.analytics.repository import AnalyticsRepository
from app.features.analytics.schemas import (
    AuditLogOut,
    DashboardOut,
    SalesSeriesOut,
    TimePoint,
    TopProduct,
    TopProductsOut,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnalyticsRepository(db)

    async def dashboard(self, start: date, end: date) -> DashboardOut:
        d = await self.repo.dashboard(start, end)
        orders = int(d["orders"])
        revenue = int(d["revenue"])
        aov = revenue // orders if orders else 0
        return DashboardOut(
            revenue=revenue, orders=orders, new_customers=int(d["new_customers"]),
            avg_order_value=aov, delivered=int(d["delivered"]), cancelled=int(d["cancelled"]),
        )

    async def sales(self, start: date, end: date) -> SalesSeriesOut:
        rows = await self.repo.sales_series(start, end)
        return SalesSeriesOut(points=[
            TimePoint(date=str(r["d"]), revenue=int(r["revenue"]), orders=int(r["orders"])) for r in rows
        ])

    async def top_products(self, start: date, end: date) -> TopProductsOut:
        rows = await self.repo.top_products(start, end)
        return TopProductsOut(products=[
            TopProduct(product_name=r["product_name"], units=int(r["units"]), revenue=int(r["revenue"]))
            for r in rows
        ])

    async def audit_logs(self, params: PageParams) -> Page[AuditLogOut]:
        rows = await self.repo.list_audit(params.offset, params.limit)
        items = [AuditLogOut(id=r.id, actor_id=r.actor_id, action=r.action,
                             entity_type=r.entity_type, entity_id=r.entity_id, created_at=r.created_at)
                 for r in rows]
        return build_page(items, len(items) + params.offset, params)

    async def log(self, actor_id: uuid.UUID | None, action: str, entity_type: str | None = None,
                  entity_id: uuid.UUID | None = None, before: dict | None = None,
                  after: dict | None = None, ip: str | None = None, ua: str | None = None) -> None:
        await self.repo.write_audit(AuditLog(
            actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id,
            before=before, after=after, ip=ip, user_agent=ua,
        ))
