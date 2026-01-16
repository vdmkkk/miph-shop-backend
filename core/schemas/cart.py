from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from core.schemas.base import CamelModel


class CartItemSchema(CamelModel):
    variant_id: str
    item_id: str
    slug: str
    title: str
    variant_title: str
    sku: str
    qty: int
    unit_price_rub: Decimal
    line_total_rub: Decimal
    available: bool
    stock: int
    image_url: str | None


class CartTotalsSchema(CamelModel):
    items_count: int
    subtotal_rub: Decimal


class CartSchema(CamelModel):
    id: str
    items: list[CartItemSchema]
    totals: CartTotalsSchema
    updated_at: datetime


class CartResponse(CamelModel):
    cart: CartSchema


class CartMergeWarning(CamelModel):
    variant_id: str
    reason: str


class CartMergeResponse(CamelModel):
    cart: CartSchema
    merge_warnings: list[CartMergeWarning]
