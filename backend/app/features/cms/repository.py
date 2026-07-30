"""CMS data access."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Product
from app.features.cms.models import (
    Banner,
    CmsPage,
    CmsSetting,
    HomeSection,
    HomeSectionItem,
    OnboardingSlide,
)


class CmsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ----- settings -----
    async def settings_by_group(self, *groups: str) -> list[CmsSetting]:
        stmt = select(CmsSetting)
        if groups:
            stmt = stmt.where(CmsSetting.group_key.in_(groups))
        return list((await self.db.execute(stmt)).scalars().all())

    async def upsert_setting(self, group_key: str, key: str, value) -> CmsSetting:
        res = await self.db.execute(
            select(CmsSetting).where(CmsSetting.group_key == group_key, CmsSetting.key == key)
        )
        s = res.scalar_one_or_none()
        if s is None:
            s = CmsSetting(group_key=group_key, key=key, value=value)
            self.db.add(s)
        else:
            s.value = value
        await self.db.flush()
        return s

    # ----- home layout -----
    async def active_sections(self) -> list[HomeSection]:
        res = await self.db.execute(
            select(HomeSection).where(HomeSection.is_active.is_(True)).order_by(HomeSection.sort_order)
        )
        return list(res.scalars().all())

    async def section_products(self, section_id: uuid.UUID) -> list[Product]:
        res = await self.db.execute(
            select(Product)
            .join(HomeSectionItem, HomeSectionItem.product_id == Product.id)
            .where(HomeSectionItem.section_id == section_id, Product.deleted_at.is_(None))
            .order_by(HomeSectionItem.sort_order)
        )
        return list(res.scalars().all())

    async def dynamic_products(self, section_type: str, limit: int) -> list[Product]:
        stmt = select(Product).where(Product.deleted_at.is_(None), Product.is_active.is_(True))
        if section_type in ("recently_added",):
            stmt = stmt.order_by(Product.created_at.desc())
        elif section_type in ("popular", "trending", "recommended"):
            stmt = stmt.order_by(Product.rating_avg.desc(), Product.rating_count.desc())
        else:
            stmt = stmt.order_by(Product.created_at.desc())
        return list((await self.db.execute(stmt.limit(limit))).scalars().all())

    # ----- banners -----
    async def banners(self, placement: str | None = None) -> list[Banner]:
        stmt = select(Banner).where(Banner.is_active.is_(True)).order_by(Banner.sort_order)
        if placement:
            stmt = stmt.where(Banner.placement == placement)
        return list((await self.db.execute(stmt)).scalars().all())

    async def add_banner(self, banner: Banner) -> Banner:
        self.db.add(banner)
        await self.db.flush()
        return banner

    # ----- onboarding -----
    async def onboarding(self) -> list[OnboardingSlide]:
        res = await self.db.execute(
            select(OnboardingSlide).where(OnboardingSlide.is_active.is_(True)).order_by(OnboardingSlide.sort_order)
        )
        return list(res.scalars().all())

    # ----- pages -----
    async def page(self, slug: str) -> CmsPage | None:
        res = await self.db.execute(select(CmsPage).where(CmsPage.slug == slug))
        return res.scalar_one_or_none()

    async def upsert_page(self, data: dict, updated_by: uuid.UUID | None) -> CmsPage:
        res = await self.db.execute(select(CmsPage).where(CmsPage.slug == data["slug"]))
        page = res.scalar_one_or_none()
        if page is None:
            page = CmsPage(**data, updated_by=updated_by)
            self.db.add(page)
        else:
            for k, v in data.items():
                setattr(page, k, v)
            page.version += 1
            page.updated_by = updated_by
        await self.db.flush()
        return page
