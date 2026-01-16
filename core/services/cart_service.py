from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models.cart import Cart, CartItem
from core.models.catalog import Item, ItemImage, ItemVariant
from core.schemas.cart import CartSchema, CartItemSchema, CartTotalsSchema


@dataclass
class MergeWarning:
    variant_id: str
    reason: str


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _to_uuid(value: str | uuid.UUID) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


async def get_or_create_cart(session: AsyncSession, user_id: str) -> Cart:
    user_uuid = _to_uuid(user_id)
    cart = await session.scalar(select(Cart).where(Cart.user_id == user_uuid))
    if cart is None:
        cart = Cart(user_id=user_uuid)
        session.add(cart)
        await session.commit()
        await session.refresh(cart)
    return cart


async def build_cart_schema(session: AsyncSession, user_id: str) -> CartSchema:
    user_uuid = _to_uuid(user_id)
    cart = await session.scalar(
        select(Cart)
        .where(Cart.user_id == user_uuid)
        .options(selectinload(Cart.items))
    )
    if cart is None:
        cart = await get_or_create_cart(session, user_id)

    if not cart.items:
        return CartSchema(
            id=str(cart.id),
            items=[],
            totals=CartTotalsSchema(items_count=0, subtotal_rub=Decimal("0.00")),
            updated_at=cart.updated_at,
        )

    variant_ids = [item.variant_id for item in cart.items]
    variants = await session.scalars(
        select(ItemVariant)
        .where(ItemVariant.id.in_(variant_ids))
        .options(selectinload(ItemVariant.item).selectinload(Item.images))
    )
    variant_map = {variant.id: variant for variant in variants}

    items_payload: list[CartItemSchema] = []
    items_count = 0
    subtotal = Decimal("0.00")

    for cart_item in cart.items:
        variant = variant_map.get(cart_item.variant_id)
        if variant is None:
            continue
        item: Item = variant.item
        main_image = _get_main_image(item)
        available = variant.is_active and variant.stock > 0
        line_total = (variant.price_rub or Decimal("0.00")) * cart_item.qty
        items_payload.append(
            CartItemSchema(
                variant_id=str(variant.id),
                item_id=str(item.id),
                slug=item.slug,
                title=item.title,
                variant_title=variant.title,
                sku=variant.sku,
                qty=cart_item.qty,
                unit_price_rub=variant.price_rub,
                line_total_rub=line_total,
                available=available,
                stock=variant.stock,
                image_url=main_image.url if main_image else None,
            )
        )
        items_count += cart_item.qty
        subtotal += line_total

    return CartSchema(
        id=str(cart.id),
        items=items_payload,
        totals=CartTotalsSchema(items_count=items_count, subtotal_rub=subtotal),
        updated_at=cart.updated_at,
    )


def _get_main_image(item: Item) -> ItemImage | None:
    if not item.images:
        return None
    for image in item.images:
        if image.is_main:
            return image
    return item.images[0]


async def merge_cart(
    session: AsyncSession, user_id: str, mode: str, items: list[dict[str, int]]
) -> tuple[CartSchema, list[MergeWarning]]:
    cart = await get_or_create_cart(session, user_id)
    warnings: list[MergeWarning] = []

    variant_ids = [_to_uuid(entry["variantId"]) for entry in items]
    variants = await session.scalars(
        select(ItemVariant).where(ItemVariant.id.in_(variant_ids))
    )
    variant_map = {str(variant.id): variant for variant in variants}

    if mode == "replace":
        await session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))

    existing_items = await session.scalars(
        select(CartItem).where(CartItem.cart_id == cart.id)
    )
    existing_map = {str(item.variant_id): item for item in existing_items}

    for entry in items:
        variant_id = entry["variantId"]
        qty = entry["qty"]
        variant = variant_map.get(variant_id)
        if variant is None:
            warnings.append(MergeWarning(variant_id=variant_id, reason="variant_not_found"))
            continue
        if not variant.is_active or variant.stock <= 0:
            warnings.append(MergeWarning(variant_id=variant_id, reason="out_of_stock"))
            continue

        if mode == "add":
            qty = qty + existing_map.get(variant_id, CartItem(qty=0)).qty
        elif mode == "max":
            qty = max(qty, existing_map.get(variant_id, CartItem(qty=0)).qty)

        if qty > variant.stock:
            qty = variant.stock
            warnings.append(MergeWarning(variant_id=variant_id, reason="out_of_stock"))

        if qty <= 0:
            continue

        cart_item = existing_map.get(variant_id)
        if cart_item is None:
            cart_item = CartItem(cart_id=cart.id, variant_id=variant.id, qty=qty)
            session.add(cart_item)
        else:
            cart_item.qty = qty

    cart.updated_at = _now()
    await session.commit()

    cart_schema = await build_cart_schema(session, user_id)
    return cart_schema, warnings


async def update_cart_item(
    session: AsyncSession, user_id: str, variant_id: str, qty: int
) -> CartSchema:
    cart = await get_or_create_cart(session, user_id)
    variant_uuid = _to_uuid(variant_id)
    cart_item = await session.scalar(
        select(CartItem)
        .where(CartItem.cart_id == cart.id)
        .where(CartItem.variant_id == variant_uuid)
    )
    if cart_item is None:
        cart_item = CartItem(cart_id=cart.id, variant_id=variant_uuid, qty=qty)
        session.add(cart_item)
    else:
        cart_item.qty = qty
    cart.updated_at = _now()
    await session.commit()
    return await build_cart_schema(session, user_id)


async def delete_cart_item(
    session: AsyncSession, user_id: str, variant_id: str
) -> CartSchema:
    cart = await get_or_create_cart(session, user_id)
    variant_uuid = _to_uuid(variant_id)
    await session.execute(
        delete(CartItem)
        .where(CartItem.cart_id == cart.id)
        .where(CartItem.variant_id == variant_uuid)
    )
    cart.updated_at = _now()
    await session.commit()
    return await build_cart_schema(session, user_id)


async def clear_cart(session: AsyncSession, user_id: str) -> CartSchema:
    cart = await get_or_create_cart(session, user_id)
    await session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    await session.execute(
        update(Cart).where(Cart.id == cart.id).values(updated_at=_now())
    )
    await session.commit()
    return await build_cart_schema(session, user_id)
