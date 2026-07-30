"""Catalog transport: public read + admin CRUD + wishlist."""
from __future__ import annotations

import uuid
from dataclasses import asdict  # noqa: F401  (reserved for future)

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_customer, require_permission
from app.core.pagination import Page, PageParams
from app.db.session import get_db
from app.features.auth.models import User
from app.features.catalog.schemas import (
    CategoryCreate,
    CategoryOut,
    ProductCard,
    ProductCreate,
    ProductDetail,
    ProductUpdate,
    VariantCreate,
    VariantOut,
)
from app.features.catalog.service import CatalogService

# ---------------- public ----------------
router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut])
async def categories(db: AsyncSession = Depends(get_db)):
    return await CatalogService(db).category_tree()


@router.get("/products", response_model=Page[ProductCard])
async def products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = None,
    category_id: uuid.UUID | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    params = PageParams(page=page, page_size=page_size, sort=sort)
    return await CatalogService(db).list_products(params, category_id, q)


@router.get("/products/{slug}", response_model=ProductDetail)
async def product_detail(slug: str, db: AsyncSession = Depends(get_db)):
    return await CatalogService(db).product_detail(slug)


# ---------------- wishlist (customer) ----------------
@router.get("/me/wishlist", response_model=list[ProductCard], tags=["wishlist"])
async def wishlist(user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    return await CatalogService(db).list_wishlist(user.id)


@router.post("/me/wishlist/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["wishlist"])
async def add_wishlist(product_id: uuid.UUID, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    await CatalogService(db).add_wishlist(user.id, product_id)


@router.delete("/me/wishlist/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["wishlist"])
async def remove_wishlist(product_id: uuid.UUID, user: User = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    await CatalogService(db).remove_wishlist(user.id, product_id)


# ---------------- admin ----------------
admin_router = APIRouter(prefix="/admin", tags=["admin:catalog"])


@admin_router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(body: CategoryCreate, _: User = Depends(require_permission("category.manage")), db: AsyncSession = Depends(get_db)):
    return await CatalogService(db).create_category(body)


@admin_router.post("/products", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
async def create_product(body: ProductCreate, _: User = Depends(require_permission("product.create")), db: AsyncSession = Depends(get_db)):
    return await CatalogService(db).create_product(body)


@admin_router.patch("/products/{product_id}", response_model=ProductDetail)
async def update_product(product_id: uuid.UUID, body: ProductUpdate, _: User = Depends(require_permission("product.update")), db: AsyncSession = Depends(get_db)):
    return await CatalogService(db).update_product(product_id, body)


@admin_router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: uuid.UUID, _: User = Depends(require_permission("product.delete")), db: AsyncSession = Depends(get_db)):
    await CatalogService(db).delete_product(product_id)


@admin_router.post("/products/{product_id}/variants", response_model=VariantOut, status_code=status.HTTP_201_CREATED)
async def add_variant(product_id: uuid.UUID, body: VariantCreate, _: User = Depends(require_permission("product.update")), db: AsyncSession = Depends(get_db)):
    return await CatalogService(db).add_variant(product_id, body)
