from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from core.schemas.base import CamelModel


class OrderItemSchema(CamelModel):
    id: UUID
    item_id: UUID
    variant_id: UUID
    title: str
    variant_title: str
    sku: str
    unit_price_rub: Decimal
    qty: int
    line_total_rub: Decimal


class OrderEventSchema(CamelModel):
    id: UUID
    from_status: str | None
    to_status: str
    note: str | None
    created_by: str
    created_at: datetime


class OrderDeliverySchema(CamelModel):
    method: str
    address: dict[str, Any]


class OrderContactSchema(CamelModel):
    name: str
    phone: str
    email: str


class OrderSchema(CamelModel):
    id: UUID
    status: str
    subtotal_rub: Decimal
    delivery_rub: Decimal
    total_rub: Decimal
    placed_at: datetime
    items: list[OrderItemSchema]
    delivery: OrderDeliverySchema
    contact: OrderContactSchema
    events: list[OrderEventSchema]


class OrderResponse(CamelModel):
    order: OrderSchema
