"""CMS use-cases: public storefront reads + admin content management."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.features.auth.models import User
from app.features.catalog.models import Product
from app.features.catalog.schemas import ProductCard
from app.features.cms.models import Banner
from app.features.cms.repository import CmsRepository
from app.features.cms.schemas import (
    BannerIn,
    BannerOut,
    BrandingOut,
    HomeLayoutOut,
    HomeSectionOut,
    OnboardingSlideOut,
    PageIn,
    PageOut,
)

_BANNER_TYPES = {"hero", "offer", "banner", "bottom_banner"}


def _card(p: Product) -> ProductCard:
    imgs = sorted(p.media, key=lambda m: (not m.is_primary, m.sort_order))
    return ProductCard(
        id=p.id, name=p.name, slug=p.slug, short_description=p.short_description,
        brand=p.brand, is_veg=p.is_veg, rating_avg=float(p.rating_avg),
        rating_count=p.rating_count, primary_image=imgs[0].url if imgs else None,
        price_from=min((v.price_amount for v in p.variants if v.is_active), default=None),
    )


def _banner_out(b: Banner) -> BannerOut:
    return BannerOut(id=b.id, title=b.title, image_url=b.image_url, placement=b.placement,
                     target_type=b.target_type, target_ref=b.target_ref)


class CmsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CmsRepository(db)

    async def home(self) -> HomeLayoutOut:
        sections = await self.repo.active_sections()
        out: list[HomeSectionOut] = []
        for s in sections:
            limit = int((s.config or {}).get("limit", 10))
            if s.type in _BANNER_TYPES:
                banners = await self.repo.banners(placement=s.type)
                out.append(HomeSectionOut(id=s.id, type=s.type, title=s.title,
                                          banners=[_banner_out(b) for b in banners]))
                continue
            picked = await self.repo.section_products(s.id)
            products = picked or await self.repo.dynamic_products(s.type, limit)
            out.append(HomeSectionOut(id=s.id, type=s.type, title=s.title,
                                      items=[_card(p) for p in products]))
        return HomeLayoutOut(sections=out)

    async def banners(self, placement: str | None) -> list[BannerOut]:
        return [_banner_out(b) for b in await self.repo.banners(placement)]

    async def onboarding(self) -> list[OnboardingSlideOut]:
        return [
            OnboardingSlideOut(id=s.id, title=s.title, subtitle=s.subtitle, image_url=s.image_url)
            for s in await self.repo.onboarding()
        ]

    async def branding(self) -> BrandingOut:
        settings = await self.repo.settings_by_group("branding", "theme", "contact")
        return BrandingOut(settings={f"{s.group_key}.{s.key}": s.value for s in settings})

    async def page(self, slug: str) -> PageOut:
        page = await self.repo.page(slug)
        if page is None or page.status != "published":
            raise NotFound("Page not found.")
        return PageOut(slug=page.slug, title=page.title, body=page.body)

    # ----- admin -----
    async def put_setting(self, group_key: str, key: str, value) -> dict:
        s = await self.repo.upsert_setting(group_key, key, value)
        return {"group_key": s.group_key, "key": s.key, "value": s.value}

    async def create_banner(self, body: BannerIn) -> BannerOut:
        b = await self.repo.add_banner(Banner(**body.model_dump()))
        return _banner_out(b)

    async def upsert_page(self, body: PageIn, actor: User) -> PageOut:
        page = await self.repo.upsert_page(body.model_dump(), actor.id)
        return PageOut(slug=page.slug, title=page.title, body=page.body)
