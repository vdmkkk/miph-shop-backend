from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from core.schemas.base import CamelModel


class CategorySchema(CamelModel):
    id: UUID
    slug: str
    title: str
    parent_id: UUID | None
    is_active: bool
    sort_rank: int


class TagSchema(CamelModel):
    id: UUID
    slug: str
    title: str
    is_active: bool


class VariantSchema(CamelModel):
    id: UUID
    sku: str
    title: str
    attributes: dict[str, Any]
    price_rub: Decimal
    compare_at_price_rub: Decimal | None
    stock: int
    is_active: bool


class ItemImageSchema(CamelModel):
    id: UUID
    url: str
    alt: str | None
    sort_order: int
    is_main: bool


class ItemListSchema(CamelModel):
    id: UUID
    slug: str
    title: str
    short_description: str | None = None
    is_active: bool
    main_image_url: str | None = None
    min_price_rub: Decimal | None
    max_price_rub: Decimal | None
    has_stock: bool
    category_slugs: list[str]
    tag_slugs: list[str]


class ItemDetailSchema(CamelModel):
    id: UUID
    slug: str
    title: str
    description: str
    brand: str | None
    is_active: bool
    categories: list[CategorySchema]
    tags: list[TagSchema]
    images: list[ItemImageSchema]
    variants: list[VariantSchema]


class ItemDetailResponse(CamelModel):
    item: ItemDetailSchema


class CategoryListResponse(CamelModel):
    data: list[CategorySchema]


class TagListResponse(CamelModel):
    data: list[TagSchema]
