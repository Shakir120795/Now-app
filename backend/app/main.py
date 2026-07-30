"""FastAPI application factory.

Feature routers are mounted under the versioned prefix as they are implemented in
Phase 1. Keeping the factory here means tests and workers can import a clean app.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.features.analytics.router import admin_router as analytics_admin_router
from app.features.auth.router import router as auth_router
from app.features.delivery.router import router as delivery_router
from app.features.cart.router import router as cart_router
from app.features.catalog.router import admin_router as catalog_admin_router
from app.features.catalog.router import router as catalog_router
from app.features.cms.router import admin_router as cms_admin_router
from app.features.cms.router import router as cms_router
from app.features.notifications.router import admin_router as notifications_admin_router
from app.features.notifications.router import router as notifications_router
from app.features.orders.router import admin_router as orders_admin_router
from app.features.orders.router import router as orders_router
from app.features.payments.router import router as payments_router
from app.features.promotions.router import admin_router as promotions_admin_router
from app.features.promotions.router import router as promotions_router
from app.features.reviews.router import router as reviews_router
from app.features.search.router import router as search_router
from app.features.users.router import admin_router as users_admin_router
from app.features.users.router import router as users_router
from app.features.wallet.router import admin_router as wallet_admin_router
from app.features.wallet.router import router as wallet_router

# Feature routers, mounted under the versioned prefix. Append as modules land.
FEATURE_ROUTERS: list = [
    auth_router,
    users_router,
    users_admin_router,
    catalog_router,
    catalog_admin_router,
    search_router,
    cart_router,
    orders_router,
    orders_admin_router,
    payments_router,
    wallet_router,
    wallet_admin_router,
    promotions_router,
    promotions_admin_router,
    reviews_router,
    cms_router,
    cms_admin_router,
    notifications_router,
    notifications_admin_router,
    delivery_router,
    analytics_admin_router,
]


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten per environment in Phase 5
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "env": settings.env}

    for router in FEATURE_ROUTERS:
        app.include_router(router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
