from __future__ import annotations

from decimal import Decimal
import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models.catalog import (
    Category,
    Item,
    ItemCategory,
    ItemImage,
    ItemTag,
    ItemVariant,
    Tag,
)
from core.schemas.catalog import ItemDetailSchema, ItemImageSchema, VariantSchema


async def list_categories(
    session: AsyncSession, page: int, per_page: int
) -> tuple[list[Category], int]:
    base = select(Category)
    count_stmt = select(func.count()).select_from(base.subquery())
    total = await session.scalar(count_stmt) or 0
    rows = await session.scalars(
        base.order_by(Category.sort_rank.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return list(rows), total


async def create_category(session: AsyncSession, payload: dict) -> Category:
    category = Category(**payload)
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


def _to_uuid(value: str | uuid.UUID) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


async def update_category(
    session: AsyncSession, category_id: str, payload: dict
) -> Category | None:
    category = await session.scalar(
        select(Category).where(Category.id == _to_uuid(category_id))
    )
    if category is None:
        return None
    for key, value in payload.items():
        if value is not None:
            setattr(category, key, value)
    await session.commit()
    await session.refresh(category)
    return category


async def delete_category(session: AsyncSession, category_id: str) -> Category | None:
    category = await session.scalar(
        select(Category).where(Category.id == _to_uuid(category_id))
    )
    if category is None:
        return None
    category.is_active = False
    await session.commit()
    await session.refresh(category)
    return category


async def list_tags(session: AsyncSession, page: int, per_page: int) -> tuple[list[Tag], int]:
    base = select(Tag)
    count_stmt = select(func.count()).select_from(base.subquery())
    total = await session.scalar(count_stmt) or 0
    rows = await session.scalars(
        base.order_by(Tag.title.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return list(rows), total


async def create_tag(session: AsyncSession, payload: dict) -> Tag:
    tag = Tag(**payload)
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


async def update_tag(session: AsyncSession, tag_id: str, payload: dict) -> Tag | None:
    tag = await session.scalar(select(Tag).where(Tag.id == _to_uuid(tag_id)))
    if tag is None:
        return None
    for key, value in payload.items():
        if value is not None:
            setattr(tag, key, value)
    await session.commit()
    await session.refresh(tag)
    return tag


async def delete_tag(session: AsyncSession, tag_id: str) -> Tag | None:
    tag = await session.scalar(select(Tag).where(Tag.id == _to_uuid(tag_id)))
    if tag is None:
        return None
    tag.is_active = False
    await session.commit()
    await session.refresh(tag)
    return tag


async def list_items(
    session: AsyncSession,
    q: str | None,
    is_active: bool | None,
    category: str | None,
    tag: str | None,
    page: int,
    per_page: int,
) -> tuple[list[Item], int]:
    stmt = select(Item)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(Item.title).like(like) | func.lower(Item.description).like(like)
        )
    if is_active is not None:
        stmt = stmt.where(Item.is_active.is_(is_active))
    if category:
        stmt = stmt.join(ItemCategory, ItemCategory.item_id == Item.id).join(
            Category, Category.id == ItemCategory.category_id
        )
        stmt = stmt.where(Category.slug == category)
    if tag:
        stmt = stmt.join(ItemTag, ItemTag.item_id == Item.id).join(
            Tag, Tag.id == ItemTag.tag_id
        )
        stmt = stmt.where(Tag.slug == tag)

    stmt = stmt.distinct()
    count_stmt = select(func.count()).select_from(
        stmt.with_only_columns(Item.id).subquery()
    )
    total = await session.scalar(count_stmt) or 0
    rows = await session.scalars(
        stmt.order_by(Item.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return list(rows), total


async def create_item(session: AsyncSession, payload: dict) -> Item:
    category_ids = [_to_uuid(value) for value in payload.pop("category_ids", [])]
    tag_ids = [_to_uuid(value) for value in payload.pop("tag_ids", [])]
    item = Item(**payload)
    session.add(item)
    await session.flush()

    if category_ids:
        session.add_all(
            [
                ItemCategory(item_id=item.id, category_id=category_id)
                for category_id in category_ids
            ]
        )
    if tag_ids:
        session.add_all(
            [ItemTag(item_id=item.id, tag_id=tag_id) for tag_id in tag_ids]
        )
    await session.commit()
    await session.refresh(item)
    return item


async def update_item(session: AsyncSession, item_id: str, payload: dict) -> Item | None:
    item = await session.scalar(select(Item).where(Item.id == _to_uuid(item_id)))
    if item is None:
        return None

    category_ids = payload.pop("category_ids", None)
    tag_ids = payload.pop("tag_ids", None)

    for key, value in payload.items():
        if value is not None:
            setattr(item, key, value)

    if category_ids is not None:
        category_ids = [_to_uuid(value) for value in category_ids]
        await session.execute(delete(ItemCategory).where(ItemCategory.item_id == item.id))
        if category_ids:
            session.add_all(
                [
                    ItemCategory(item_id=item.id, category_id=category_id)
                    for category_id in category_ids
                ]
            )
    if tag_ids is not None:
        tag_ids = [_to_uuid(value) for value in tag_ids]
        await session.execute(delete(ItemTag).where(ItemTag.item_id == item.id))
        if tag_ids:
            session.add_all([ItemTag(item_id=item.id, tag_id=tag_id) for tag_id in tag_ids])

    await session.commit()
    await session.refresh(item)
    return item


async def delete_item(session: AsyncSession, item_id: str) -> Item | None:
    item = await session.scalar(select(Item).where(Item.id == _to_uuid(item_id)))
    if item is None:
        return None
    item.is_active = False
    await session.commit()
    await session.refresh(item)
    return item


async def create_item_image(session: AsyncSession, item_id: str, payload: dict) -> ItemImage:
    item_uuid = _to_uuid(item_id)
    image = ItemImage(item_id=item_uuid, **payload)
    session.add(image)
    await session.flush()

    if image.is_main:
        await session.execute(
            update(ItemImage)
            .where(ItemImage.item_id == item_uuid)
            .where(ItemImage.id != image.id)
            .values(is_main=False)
        )

    await session.commit()
    await session.refresh(image)
    return image


async def update_item_image(
    session: AsyncSession, image_id: str, payload: dict
) -> ItemImage | None:
    image = await session.scalar(
        select(ItemImage).where(ItemImage.id == _to_uuid(image_id))
    )
    if image is None:
        return None
    for key, value in payload.items():
        if value is not None:
            setattr(image, key, value)
    await session.flush()
    if image.is_main:
        await session.execute(
            update(ItemImage)
            .where(ItemImage.item_id == image.item_id)
            .where(ItemImage.id != image.id)
            .values(is_main=False)
        )
    await session.commit()
    await session.refresh(image)
    return image


async def delete_item_image(session: AsyncSession, image_id: str) -> ItemImage | None:
    image = await session.scalar(
        select(ItemImage).where(ItemImage.id == _to_uuid(image_id))
    )
    if image is None:
        return None
    await session.delete(image)
    await session.commit()
    return image


async def _recalc_item_stats(session: AsyncSession, item_id: str) -> None:
    stats = await session.execute(
        select(
            func.min(ItemVariant.price_rub),
            func.max(ItemVariant.price_rub),
            func.bool_or(
                ItemVariant.is_active.is_(True) & (ItemVariant.stock > 0)
            ),
        ).where(ItemVariant.item_id == item_id)
    )
    min_price, max_price, has_stock = stats.one()
    await session.execute(
        update(Item)
        .where(Item.id == item_id)
        .values(
            min_price_rub=min_price,
            max_price_rub=max_price,
            has_stock=has_stock if has_stock is not None else False,
        )
    )
    await session.commit()


async def create_variant(session: AsyncSession, item_id: str, payload: dict) -> ItemVariant:
    item_uuid = _to_uuid(item_id)
    variant = ItemVariant(item_id=item_uuid, **payload)
    session.add(variant)
    await session.commit()
    await _recalc_item_stats(session, item_uuid)
    await session.refresh(variant)
    return variant


async def update_variant(
    session: AsyncSession, variant_id: str, payload: dict
) -> ItemVariant | None:
    variant = await session.scalar(
        select(ItemVariant).where(ItemVariant.id == _to_uuid(variant_id))
    )
    if variant is None:
        return None
    for key, value in payload.items():
        if value is not None:
            setattr(variant, key, value)
    await session.commit()
    await _recalc_item_stats(session, variant.item_id)
    await session.refresh(variant)
    return variant


async def delete_variant(session: AsyncSession, variant_id: str) -> ItemVariant | None:
    variant = await session.scalar(
        select(ItemVariant).where(ItemVariant.id == _to_uuid(variant_id))
    )
    if variant is None:
        return None
    variant.is_active = False
    await session.commit()
    await _recalc_item_stats(session, variant.item_id)
    await session.refresh(variant)
    return variant
