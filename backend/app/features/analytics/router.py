"""Admin analytics + audit transport."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.core.pagination import Page, PageParams
from app.db.session import get_db
from app.features.analytics.schemas import (
    AuditLogOut,
    DashboardOut,
    SalesSeriesOut,
    TopProductsOut,
)
from app.features.analytics.service import AnalyticsService
from app.features.auth.models import User

admin_router = APIRouter(prefix="/admin", tags=["admin:analytics"])


def _range(from_: date | None, to: date | None) -> tuple[date, date]:
    end = to or date.today()
    start = from_ or (end - timedelta(days=30))
    return start, end


@admin_router.get("/dashboard", response_model=DashboardOut)
async def dashboard(
    from_: date | None = Query(None, alias="from"), to: date | None = None,
    _: User = Depends(require_permission("analytics.read")), db: AsyncSession = Depends(get_db),
):
    start, end = _range(from_, to)
    return await AnalyticsService(db).dashboard(start, end)


@admin_router.get("/analytics/sales", response_model=SalesSeriesOut)
async def sales(
    from_: date | None = Query(None, alias="from"), to: date | None = None,
    _: User = Depends(require_permission("analytics.read")), db: AsyncSession = Depends(get_db),
):
    start, end = _range(from_, to)
    return await AnalyticsService(db).sales(start, end)


@admin_router.get("/analytics/top-products", response_model=TopProductsOut)
async def top_products(
    from_: date | None = Query(None, alias="from"), to: date | None = None,
    _: User = Depends(require_permission("analytics.read")), db: AsyncSession = Depends(get_db),
):
    start, end = _range(from_, to)
    return await AnalyticsService(db).top_products(start, end)


@admin_router.get("/audit-logs", response_model=Page[AuditLogOut])
async def audit_logs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_permission("audit.read")), db: AsyncSession = Depends(get_db),
):
    return await AnalyticsService(db).audit_logs(PageParams(page=page, page_size=page_size))
