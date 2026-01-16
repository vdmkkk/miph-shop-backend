from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models.order import Order, OrderEvent
from core.schemas.order import (
    OrderContactSchema,
    OrderDeliverySchema,
    OrderEventSchema,
    OrderItemSchema,
    OrderSchema,
)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _to_uuid(value: str | uuid.UUID) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


def _build_order_schema(order: Order) -> OrderSchema:
    items = [
        OrderItemSchema(
            id=str(item.id),
            item_id=str(item.item_id),
            variant_id=str(item.variant_id),
            title=item.title,
            variant_title=item.variant_title,
            sku=item.sku,
            unit_price_rub=item.unit_price_rub,
            qty=item.qty,
            line_total_rub=item.line_total_rub,
        )
        for item in order.items
    ]
    events = [
        OrderEventSchema(
            id=str(event.id),
            from_status=event.from_status,
            to_status=event.to_status,
            note=event.note,
            created_by=event.created_by,
            created_at=event.created_at,
        )
        for event in order.events
    ]
    return OrderSchema(
        id=str(order.id),
        status=order.status,
        subtotal_rub=order.subtotal_rub,
        delivery_rub=order.delivery_rub,
        total_rub=order.total_rub,
        placed_at=order.placed_at,
        items=items,
        delivery=OrderDeliverySchema(
            method=order.delivery_method, address=order.delivery_address
        ),
        contact=OrderContactSchema(
            name=order.contact_name,
            phone=order.contact_phone,
            email=order.email,
        ),
        events=events,
    )


async def list_orders(
    session: AsyncSession, status: str | None, email: str | None, page: int, per_page: int
) -> tuple[list[OrderSchema], int]:
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    if email:
        stmt = stmt.where(Order.email == email)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt) or 0
    rows = await session.scalars(
        stmt.order_by(Order.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .options(selectinload(Order.items), selectinload(Order.events))
    )
    return [_build_order_schema(order) for order in rows], total


async def get_order(session: AsyncSession, order_id: str) -> OrderSchema | None:
    order = await session.scalar(
        select(Order)
        .where(Order.id == _to_uuid(order_id))
        .options(selectinload(Order.items), selectinload(Order.events))
    )
    if order is None:
        return None
    return _build_order_schema(order)


async def update_status(
    session: AsyncSession, order_id: str, to_status: str, note: str | None
) -> OrderSchema | None:
    order = await session.scalar(
        select(Order)
        .where(Order.id == _to_uuid(order_id))
        .options(selectinload(Order.items), selectinload(Order.events))
    )
    if order is None:
        return None
    order.events.append(
        OrderEvent(
            from_status=order.status,
            to_status=to_status,
            note=note,
            created_by="admin",
        )
    )
    order.status = to_status
    if to_status == "paid":
        order.paid_at = _now()
    if to_status == "canceled":
        order.canceled_at = _now()
    await session.commit()
    await session.refresh(order)
    await session.refresh(order, attribute_names=["items", "events"])
    return _build_order_schema(order)
