from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.schemas.base import CamelModel


class CategoryCreateSchema(CamelModel):
    slug: str
    title: str
    parent_id: str | None = None
    is_active: bool = True
    sort_rank: int = 0


class CategoryUpdateSchema(CamelModel):
    slug: str | None = None
    title: str | None = None
    parent_id: str | None = None
    is_active: bool | None = None
    sort_rank: int | None = None


class TagCreateSchema(CamelModel):
    slug: str
    title: str
    is_active: bool = True


class TagUpdateSchema(CamelModel):
    slug: str | None = None
    title: str | None = None
    is_active: bool | None = None


class ItemCreateSchema(CamelModel):
    slug: str
    title: str
    description: str
    brand: str | None = None
    is_active: bool = True
    sort_rank: int = 0
    category_ids: list[str] = []
    tag_ids: list[str] = []


class ItemUpdateSchema(CamelModel):
    slug: str | None = None
    title: str | None = None
    description: str | None = None
    brand: str | None = None
    is_active: bool | None = None
    sort_rank: int | None = None
    category_ids: list[str] | None = None
    tag_ids: list[str] | None = None


class ItemImageCreateSchema(CamelModel):
    url: str
    alt: str | None = None
    sort_order: int = 0
    is_main: bool = False


class ItemImageUpdateSchema(CamelModel):
    url: str | None = None
    alt: str | None = None
    sort_order: int | None = None
    is_main: bool | None = None


class VariantCreateSchema(CamelModel):
    sku: str
    title: str
    attributes: dict[str, Any]
    price_rub: Decimal
    compare_at_price_rub: Decimal | None = None
    stock: int = 0
    is_active: bool = True


class VariantUpdateSchema(CamelModel):
    sku: str | None = None
    title: str | None = None
    attributes: dict[str, Any] | None = None
    price_rub: Decimal | None = None
    compare_at_price_rub: Decimal | None = None
    stock: int | None = None
    is_active: bool | None = None


class OrderStatusUpdateSchema(CamelModel):
    to_status: str
    note: str | None = None


class UserAdminUpdateSchema(CamelModel):
    is_active: bool
