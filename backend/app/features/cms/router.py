"""CMS transport: public storefront reads + admin management."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.db.session import get_db
from app.features.auth.models import User
from app.features.cms.schemas import (
    BannerIn,
    BannerOut,
    BrandingOut,
    HomeLayoutOut,
    OnboardingSlideOut,
    PageIn,
    PageOut,
    SettingIn,
)
from app.features.cms.service import CmsService

# ---------------- public ----------------
router = APIRouter(prefix="/cms", tags=["cms"])


@router.get("/home", response_model=HomeLayoutOut)
async def home(db: AsyncSession = Depends(get_db)):
    return await CmsService(db).home()


@router.get("/banners", response_model=list[BannerOut])
async def banners(placement: str | None = None, db: AsyncSession = Depends(get_db)):
    return await CmsService(db).banners(placement)


@router.get("/onboarding", response_model=list[OnboardingSlideOut])
async def onboarding(db: AsyncSession = Depends(get_db)):
    return await CmsService(db).onboarding()


@router.get("/branding", response_model=BrandingOut)
async def branding(db: AsyncSession = Depends(get_db)):
    return await CmsService(db).branding()


@router.get("/pages/{slug}", response_model=PageOut)
async def page(slug: str, db: AsyncSession = Depends(get_db)):
    return await CmsService(db).page(slug)


# ---------------- admin ----------------
admin_router = APIRouter(prefix="/admin/cms", tags=["admin:cms"])


@admin_router.put("/settings")
async def put_setting(body: SettingIn, _: User = Depends(require_permission("cms.manage")), db: AsyncSession = Depends(get_db)):
    return await CmsService(db).put_setting(body.group_key, body.key, body.value)


@admin_router.post("/banners", response_model=BannerOut, status_code=201)
async def create_banner(body: BannerIn, _: User = Depends(require_permission("cms.manage")), db: AsyncSession = Depends(get_db)):
    return await CmsService(db).create_banner(body)


@admin_router.put("/pages", response_model=PageOut)
async def upsert_page(body: PageIn, actor: User = Depends(require_permission("cms.publish")), db: AsyncSession = Depends(get_db)):
    return await CmsService(db).upsert_page(body, actor)
