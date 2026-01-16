from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models.cart import Cart
from core.models.catalog import ItemVariant
from core.models.order import Order, OrderEvent, OrderItem
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


async def create_order_from_cart(
    session: AsyncSession,
    user_id: str,
    delivery_method: str,
    delivery_address: dict,
    contact: dict,
    comment: str | None,
) -> tuple[OrderSchema | None, list[dict]]:
    user_uuid = _to_uuid(user_id)
    cart = await session.scalar(
        select(Cart)
        .where(Cart.user_id == user_uuid)
        .options(selectinload(Cart.items))
    )
    if cart is None or not cart.items:
        return None, [{"code": "CART_EMPTY"}]

    variant_ids = [item.variant_id for item in cart.items]
    variants = await session.scalars(
        select(ItemVariant)
        .where(ItemVariant.id.in_(variant_ids))
        .options(selectinload(ItemVariant.item))
    )
    variant_map = {variant.id: variant for variant in variants}

    out_of_stock: list[dict] = []
    subtotal = Decimal("0.00")
    order_items: list[OrderItem] = []

    for cart_item in cart.items:
        variant = variant_map.get(cart_item.variant_id)
        if variant is None or not variant.is_active or variant.stock < cart_item.qty:
            out_of_stock.append(
                {"variantId": str(cart_item.variant_id), "reason": "out_of_stock"}
            )
            continue
        line_total = variant.price_rub * cart_item.qty
        subtotal += line_total
        order_items.append(
            OrderItem(
                item_id=variant.item_id,
                variant_id=variant.id,
                title=variant.item.title if variant.item else "",
                variant_title=variant.title,
                sku=variant.sku,
                unit_price_rub=variant.price_rub,
                qty=cart_item.qty,
                line_total_rub=line_total,
            )
        )

    if out_of_stock:
        return None, [{"code": "OUT_OF_STOCK", "variants": out_of_stock}]

    order = Order(
        user_id=user_uuid,
        status="placed",
        subtotal_rub=subtotal,
        delivery_rub=Decimal("0.00"),
        total_rub=subtotal,
        contact_name=contact["name"],
        contact_phone=contact["phone"],
        email=contact["email"],
        delivery_method=delivery_method,
        delivery_address=delivery_address,
        comment=comment,
    )
    order.items = order_items
    order.events = [
        OrderEvent(from_status=None, to_status="placed", note=None, created_by="system")
    ]
    session.add(order)

    for item in cart.items:
        await session.delete(item)
    cart.updated_at = _now()

    await session.commit()
    await session.refresh(order)
    await session.refresh(order, attribute_names=["items", "events"])
    return _build_order_schema(order), []


async def list_orders(
    session: AsyncSession, user_id: str, page: int, per_page: int
) -> tuple[list[OrderSchema], int]:
    user_uuid = _to_uuid(user_id)
    base = select(Order).where(Order.user_id == user_uuid)
    count_stmt = select(func.count()).select_from(base.subquery())
    total = await session.scalar(count_stmt) or 0

    rows = await session.scalars(
        base.order_by(Order.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .options(selectinload(Order.items), selectinload(Order.events))
    )
    orders = [_build_order_schema(order) for order in rows]
    return orders, total


async def get_order(
    session: AsyncSession, user_id: str, order_id: str
) -> OrderSchema | None:
    user_uuid = _to_uuid(user_id)
    order_uuid = _to_uuid(order_id)
    order = await session.scalar(
        select(Order)
        .where(Order.id == order_uuid)
        .where(Order.user_id == user_uuid)
        .options(selectinload(Order.items), selectinload(Order.events))
    )
    if order is None:
        return None
    return _build_order_schema(order)


async def cancel_order(
    session: AsyncSession, user_id: str, order_id: str
) -> OrderSchema | None:
    order = await session.scalar(
        select(Order)
        .where(Order.id == _to_uuid(order_id))
        .where(Order.user_id == _to_uuid(user_id))
        .options(selectinload(Order.items), selectinload(Order.events))
    )
    if order is None:
        return None
    if order.status not in {"placed"}:
        return None
    order.events.append(
        OrderEvent(
            from_status=order.status,
            to_status="canceled",
            note=None,
            created_by="system",
        )
    )
    order.status = "canceled"
    order.canceled_at = _now()
    await session.commit()
    await session.refresh(order)
    await session.refresh(order, attribute_names=["items", "events"])
    return _build_order_schema(order)


async def simulate_payment(
    session: AsyncSession, user_id: str, order_id: str
) -> OrderSchema | None:
    order = await session.scalar(
        select(Order)
        .where(Order.id == _to_uuid(order_id))
        .where(Order.user_id == _to_uuid(user_id))
        .options(selectinload(Order.items), selectinload(Order.events))
    )
    if order is None:
        return None
    if order.status != "placed":
        return None
    order.events.append(
        OrderEvent(
            from_status=order.status,
            to_status="paid",
            note=None,
            created_by="system",
        )
    )
    order.status = "paid"
    order.paid_at = _now()
    await session.commit()
    await session.refresh(order)
    await session.refresh(order, attribute_names=["items", "events"])
    return _build_order_schema(order)
