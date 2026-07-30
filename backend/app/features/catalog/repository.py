"""Catalog data access."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import (
    Category,
    Inventory,
    Product,
    ProductVariant,
    Wishlist,
)


class CatalogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- categories ----------
    async def all_categories(self, active_only: bool = True) -> list[Category]:
        stmt = select(Category).where(Category.deleted_at.is_(None))
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        stmt = stmt.order_by(Category.sort_order, Category.name)
        return list((await self.db.execute(stmt)).scalars().all())

    async def category_by_slug(self, slug: str) -> Category | None:
        res = await self.db.execute(
            select(Category).where(Category.slug == slug, Category.deleted_at.is_(None))
        )
        return res.scalar_one_or_none()

    async def get_category(self, category_id: uuid.UUID) -> Category | None:
        return await self.db.get(Category, category_id)

    async def add_category(self, category: Category) -> Category:
        self.db.add(category)
        await self.db.flush()
        return category

    # ---------- products ----------
    async def list_products(
        self,
        *,
        category_id: uuid.UUID | None,
        q: str | None,
        offset: int,
        limit: int,
        sort: str | None,
    ) -> tuple[list[Product], int]:
        base = select(Product).where(Product.deleted_at.is_(None), Product.is_active.is_(True))
        if category_id:
            base = base.where(Product.category_id == category_id)
        if q:
            like = f"%{q.lower()}%"
            base = base.where(func.lower(Product.name).like(like))

        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

        order = Product.created_at.desc()
        if sort == "price":
            order = Product.name  # price sorting resolves via variant min in service layer (Phase 1.5)
        elif sort == "-rating" or sort == "rating":
            order = Product.rating_avg.desc()
        elif sort == "name":
            order = Product.name

        res = await self.db.execute(base.order_by(order).offset(offset).limit(limit))
        return list(res.scalars().all()), int(total)

    async def product_by_slug(self, slug: str) -> Product | None:
        res = await self.db.execute(
            select(Product).where(Product.slug == slug, Product.deleted_at.is_(None))
        )
        return res.scalar_one_or_none()

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        return await self.db.get(Product, product_id)

    async def add_product(self, product: Product) -> Product:
        self.db.add(product)
        await self.db.flush()
        return product

    async def soft_delete_product(self, product: Product) -> None:
        product.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def min_price(self, product_id: uuid.UUID) -> int | None:
        res = await self.db.execute(
            select(func.min(ProductVariant.price_amount)).where(
                ProductVariant.product_id == product_id,
                ProductVariant.is_active.is_(True),
            )
        )
        return res.scalar_one_or_none()

    # ---------- variants / inventory ----------
    async def add_variant(self, variant: ProductVariant, initial_quantity: int) -> ProductVariant:
        self.db.add(variant)
        await self.db.flush()
        self.db.add(Inventory(variant_id=variant.id, quantity=initial_quantity))
        await self.db.flush()
        return variant

    async def set_inventory(self, variant_id: uuid.UUID, quantity: int) -> None:
        inv = await self.db.get(Inventory, variant_id)
        if inv:
            inv.quantity = quantity
            await self.db.flush()

    # ---------- wishlist ----------
    async def list_wishlist(self, user_id: uuid.UUID) -> list[Product]:
        res = await self.db.execute(
            select(Product)
            .join(Wishlist, Wishlist.product_id == Product.id)
            .where(Wishlist.user_id == user_id, Product.deleted_at.is_(None))
        )
        return list(res.scalars().all())

    async def add_wishlist(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        exists = await self.db.get(Wishlist, {"user_id": user_id, "product_id": product_id})
        if not exists:
            self.db.add(Wishlist(user_id=user_id, product_id=product_id))
            await self.db.flush()

    async def remove_wishlist(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        item = await self.db.get(Wishlist, {"user_id": user_id, "product_id": product_id})
        if item:
            await self.db.delete(item)
            await self.db.flush()
