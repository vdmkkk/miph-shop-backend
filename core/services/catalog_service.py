from __future__ import annotations

from decimal import Decimal
import uuid

from sqlalchemy import Select, and_, func, or_, select
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
from core.schemas.catalog import (
    CategorySchema,
    ItemDetailSchema,
    ItemImageSchema,
    ItemListSchema,
    TagSchema,
    VariantSchema,
)


def _short_description(text: str | None) -> str | None:
    if not text:
        return None
    snippet = text.strip().splitlines()[0]
    return snippet[:120] if len(snippet) > 120 else snippet


def _to_uuid(value: str | uuid.UUID) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


def _main_image(images: list[ItemImage]) -> ItemImage | None:
    if not images:
        return None
    for image in images:
        if image.is_main:
            return image
    return images[0]


async def list_categories(session: AsyncSession) -> list[CategorySchema]:
    rows = await session.scalars(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_rank)
    )
    return [CategorySchema.model_validate(row) for row in rows]


async def list_tags(session: AsyncSession) -> list[TagSchema]:
    rows = await session.scalars(
        select(Tag).where(Tag.is_active.is_(True)).order_by(Tag.title)
    )
    return [TagSchema.model_validate(row) for row in rows]


def _apply_item_filters(
    stmt: Select,
    q: str | None,
    category: str | None,
    tags: list[str] | None,
    price_min: Decimal | None,
    price_max: Decimal | None,
    in_stock: bool | None,
) -> Select:
    stmt = stmt.where(Item.is_active.is_(True))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(func.lower(Item.title).like(like), func.lower(Item.description).like(like))
        )
    if category:
        stmt = stmt.join(ItemCategory, ItemCategory.item_id == Item.id).join(
            Category, Category.id == ItemCategory.category_id
        )
        stmt = stmt.where(Category.slug == category)
    if tags:
        stmt = stmt.join(ItemTag, ItemTag.item_id == Item.id).join(
            Tag, Tag.id == ItemTag.tag_id
        )
        stmt = stmt.where(Tag.slug.in_(tags))
    if price_min is not None:
        stmt = stmt.where(Item.min_price_rub >= price_min)
    if price_max is not None:
        stmt = stmt.where(Item.max_price_rub <= price_max)
    if in_stock is True:
        stmt = stmt.where(Item.has_stock.is_(True))
    return stmt


def _apply_sort(stmt: Select, sort: str | None) -> Select:
    if sort == "priceAsc":
        return stmt.order_by(Item.min_price_rub.asc().nulls_last())
    if sort == "priceDesc":
        return stmt.order_by(Item.max_price_rub.desc().nulls_last())
    if sort == "titleAsc":
        return stmt.order_by(Item.title.asc())
    return stmt.order_by(Item.created_at.desc())


async def list_items(
    session: AsyncSession,
    *,
    q: str | None,
    category: str | None,
    tags: list[str] | None,
    price_min: Decimal | None,
    price_max: Decimal | None,
    in_stock: bool | None,
    sort: str | None,
    page: int,
    per_page: int,
) -> tuple[list[ItemListSchema], int]:
    base = select(Item).distinct()
    base = _apply_item_filters(base, q, category, tags, price_min, price_max, in_stock)
    base_subquery = base.with_only_columns(Item.id).subquery()
    count_stmt = select(func.count()).select_from(base_subquery)
    total = await session.scalar(count_stmt) or 0

    stmt = _apply_sort(base, sort).offset((page - 1) * per_page).limit(per_page)
    stmt = stmt.options(
        selectinload(Item.categories),
        selectinload(Item.tags),
        selectinload(Item.images),
    )
    rows = await session.scalars(stmt)

    items: list[ItemListSchema] = []
    for item in rows:
        main_image = _main_image(item.images)
        items.append(
            ItemListSchema(
                id=str(item.id),
                slug=item.slug,
                title=item.title,
                short_description=_short_description(item.description),
                is_active=item.is_active,
                main_image_url=main_image.url if main_image else None,
                min_price_rub=item.min_price_rub,
                max_price_rub=item.max_price_rub,
                has_stock=item.has_stock,
                category_slugs=[category.slug for category in item.categories],
                tag_slugs=[tag.slug for tag in item.tags],
            )
        )
    return items, total


async def get_item_detail(session: AsyncSession, slug: str) -> ItemDetailSchema | None:
    item = await session.scalar(
        select(Item)
        .where(Item.slug == slug)
        .where(Item.is_active.is_(True))
        .options(
            selectinload(Item.categories),
            selectinload(Item.tags),
            selectinload(Item.images),
            selectinload(Item.variants),
        )
    )
    if item is None:
        return None

    variants = [
        VariantSchema.model_validate(variant)
        for variant in item.variants
        if variant.is_active
    ]
    images = [ItemImageSchema.model_validate(image) for image in item.images]
    categories = [CategorySchema.model_validate(cat) for cat in item.categories]
    tags = [TagSchema.model_validate(tag) for tag in item.tags]

    return ItemDetailSchema(
        id=str(item.id),
        slug=item.slug,
        title=item.title,
        description=item.description,
        brand=item.brand,
        is_active=item.is_active,
        categories=categories,
        tags=tags,
        images=images,
        variants=variants,
    )


async def list_liked_items(
    session: AsyncSession,
    user_id: str,
    page: int,
    per_page: int,
) -> tuple[list[ItemListSchema], int]:
    from core.models.like import Like

    user_uuid = _to_uuid(user_id)
    base = (
        select(Item)
        .join(Like, Like.item_id == Item.id)
        .where(Like.user_id == user_uuid)
        .where(Item.is_active.is_(True))
        .distinct()
    )
    base_subquery = base.with_only_columns(Item.id).subquery()
    count_stmt = select(func.count()).select_from(base_subquery)
    total = await session.scalar(count_stmt) or 0

    stmt = base.order_by(Item.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    stmt = stmt.options(
        selectinload(Item.categories),
        selectinload(Item.tags),
        selectinload(Item.images),
    )
    rows = await session.scalars(stmt)

    items: list[ItemListSchema] = []
    for item in rows:
        main_image = _main_image(item.images)
        items.append(
            ItemListSchema(
                id=str(item.id),
                slug=item.slug,
                title=item.title,
                short_description=_short_description(item.description),
                is_active=item.is_active,
                main_image_url=main_image.url if main_image else None,
                min_price_rub=item.min_price_rub,
                max_price_rub=item.max_price_rub,
                has_stock=item.has_stock,
                category_slugs=[category.slug for category in item.categories],
                tag_slugs=[tag.slug for tag in item.tags],
            )
        )
    return items, total
