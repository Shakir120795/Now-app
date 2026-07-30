"""Catalog use-cases: category tree, product listing/detail, admin CRUD, wishlist."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, NotFound
from app.core.pagination import Page, PageParams, build_page
from app.features.catalog.models import Category, Product, ProductVariant
from app.features.catalog.repository import CatalogRepository
from app.features.catalog.schemas import (
    AddonGroupOut,
    AddonOut,
    CategoryCreate,
    CategoryOut,
    InventoryOut,
    MediaOut,
    ProductCard,
    ProductCreate,
    ProductDetail,
    ProductUpdate,
    VariantCreate,
    VariantOut,
)


def _primary_image(product: Product) -> str | None:
    imgs = sorted(product.media, key=lambda m: (not m.is_primary, m.sort_order))
    return imgs[0].url if imgs else None


def _variant_out(v: ProductVariant) -> VariantOut:
    inv = v.inventory
    return VariantOut(
        id=v.id, name=v.name, sku=v.sku, price_amount=v.price_amount,
        compare_at_amount=v.compare_at_amount, is_active=v.is_active,
        inventory=InventoryOut(quantity=inv.quantity, available=inv.available, track=inv.track)
        if inv else None,
    )


def _detail(product: Product) -> ProductDetail:
    return ProductDetail(
        id=product.id, category_id=product.category_id, name=product.name, slug=product.slug,
        short_description=product.short_description, description=product.description,
        ingredients=product.ingredients, nutrition=product.nutrition, brand=product.brand,
        is_veg=product.is_veg, delivery_eta_minutes=product.delivery_eta_minutes,
        rating_avg=float(product.rating_avg), rating_count=product.rating_count,
        media=[MediaOut(id=m.id, url=m.url, thumb_url=m.thumb_url, type=m.type, is_primary=m.is_primary)
               for m in sorted(product.media, key=lambda m: m.sort_order)],
        variants=[_variant_out(v) for v in sorted(product.variants, key=lambda v: v.sort_order)],
        addon_groups=[
            AddonGroupOut(
                id=g.id, name=g.name, min_select=g.min_select, max_select=g.max_select,
                is_required=g.is_required,
                addons=[AddonOut(id=a.id, name=a.name, price_amount=a.price_amount, is_active=a.is_active)
                        for a in sorted(g.addons, key=lambda a: a.sort_order)],
            )
            for g in sorted(product.addon_groups, key=lambda g: g.sort_order)
        ],
    )


class CatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CatalogRepository(db)

    # ---------- categories ----------
    async def category_tree(self) -> list[CategoryOut]:
        cats = await self.repo.all_categories(active_only=True)
        nodes: dict[uuid.UUID, CategoryOut] = {
            c.id: CategoryOut(
                id=c.id, name=c.name, slug=c.slug, description=c.description,
                image_url=c.image_url, icon_url=c.icon_url, sort_order=c.sort_order,
                is_active=c.is_active, parent_id=c.parent_id,
                seo_title=c.seo_title, seo_description=c.seo_description, children=[],
            )
            for c in cats
        }
        roots: list[CategoryOut] = []
        for c in cats:
            node = nodes[c.id]
            if c.parent_id and c.parent_id in nodes:
                nodes[c.parent_id].children.append(node)
            else:
                roots.append(node)
        return roots

    async def create_category(self, data: CategoryCreate) -> CategoryOut:
        if await self.repo.category_by_slug(data.slug):
            raise Conflict(f"Category slug '{data.slug}' already exists.")
        cat = await self.repo.add_category(Category(**data.model_dump()))
        return CategoryOut(**data.model_dump(), id=cat.id, children=[])

    # ---------- products ----------
    async def list_products(
        self, params: PageParams, category_id: uuid.UUID | None, q: str | None
    ) -> Page[ProductCard]:
        products, total = await self.repo.list_products(
            category_id=category_id, q=q, offset=params.offset, limit=params.limit, sort=params.sort
        )
        cards = []
        for p in products:
            price = min((v.price_amount for v in p.variants if v.is_active), default=None)
            cards.append(ProductCard(
                id=p.id, name=p.name, slug=p.slug, short_description=p.short_description,
                brand=p.brand, is_veg=p.is_veg, rating_avg=float(p.rating_avg),
                rating_count=p.rating_count, primary_image=_primary_image(p), price_from=price,
            ))
        return build_page(cards, total, params)

    async def product_detail(self, slug: str) -> ProductDetail:
        product = await self.repo.product_by_slug(slug)
        if product is None:
            raise NotFound("Product not found.")
        return _detail(product)

    async def create_product(self, data: ProductCreate) -> ProductDetail:
        if await self.repo.product_by_slug(data.slug):
            raise Conflict(f"Product slug '{data.slug}' already exists.")
        product = await self.repo.add_product(Product(**data.model_dump()))
        await self.db.refresh(product)
        return _detail(product)

    async def update_product(self, product_id: uuid.UUID, data: ProductUpdate) -> ProductDetail:
        product = await self.repo.get_product(product_id)
        if product is None or product.deleted_at is not None:
            raise NotFound("Product not found.")
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(product, k, v)
        await self.db.flush()
        await self.db.refresh(product)
        return _detail(product)

    async def delete_product(self, product_id: uuid.UUID) -> None:
        product = await self.repo.get_product(product_id)
        if product is None:
            raise NotFound("Product not found.")
        await self.repo.soft_delete_product(product)

    async def add_variant(self, product_id: uuid.UUID, data: VariantCreate) -> VariantOut:
        product = await self.repo.get_product(product_id)
        if product is None:
            raise NotFound("Product not found.")
        variant = ProductVariant(
            product_id=product_id, name=data.name, sku=data.sku,
            price_amount=data.price_amount, compare_at_amount=data.compare_at_amount,
        )
        variant = await self.repo.add_variant(variant, data.initial_quantity)
        await self.db.refresh(variant)
        return _variant_out(variant)

    # ---------- wishlist ----------
    async def list_wishlist(self, user_id: uuid.UUID) -> list[ProductCard]:
        products = await self.repo.list_wishlist(user_id)
        return [
            ProductCard(
                id=p.id, name=p.name, slug=p.slug, short_description=p.short_description,
                brand=p.brand, is_veg=p.is_veg, rating_avg=float(p.rating_avg),
                rating_count=p.rating_count, primary_image=_primary_image(p),
                price_from=min((v.price_amount for v in p.variants if v.is_active), default=None),
            )
            for p in products
        ]

    async def add_wishlist(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        if await self.repo.get_product(product_id) is None:
            raise NotFound("Product not found.")
        await self.repo.add_wishlist(user_id, product_id)

    async def remove_wishlist(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self.repo.remove_wishlist(user_id, product_id)
