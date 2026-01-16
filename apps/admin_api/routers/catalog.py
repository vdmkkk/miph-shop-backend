from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import require_admin
from core.db import get_session
from core.schemas import (
    CategoryCreateSchema,
    CategorySchema,
    CategoryUpdateSchema,
    ItemCreateSchema,
    ItemImageCreateSchema,
    ItemImageSchema,
    ItemImageUpdateSchema,
    ItemListSchema,
    ItemUpdateSchema,
    PaginatedResponse,
    TagCreateSchema,
    TagSchema,
    TagUpdateSchema,
    VariantCreateSchema,
    VariantSchema,
    VariantUpdateSchema,
)
from core.services import admin_catalog_service

router = APIRouter(prefix="/admin/v1", tags=["admin-catalog"], dependencies=[Depends(require_admin)])


@router.get("/categories", response_model=PaginatedResponse[CategorySchema])
async def list_categories(
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100, alias="perPage"),
):
    categories, total = await admin_catalog_service.list_categories(session, page, per_page)
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    return PaginatedResponse[CategorySchema](
        data=[CategorySchema.model_validate(cat) for cat in categories],
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


@router.post("/categories", response_model=CategorySchema)
async def create_category(
    payload: CategoryCreateSchema,
    session: AsyncSession = Depends(get_session),
):
    category = await admin_catalog_service.create_category(session, payload.model_dump())
    return CategorySchema.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategorySchema)
async def update_category(
    category_id: str,
    payload: CategoryUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    category = await admin_catalog_service.update_category(
        session, category_id, payload.model_dump()
    )
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return CategorySchema.model_validate(category)


@router.delete("/categories/{category_id}", response_model=CategorySchema)
async def delete_category(
    category_id: str,
    session: AsyncSession = Depends(get_session),
):
    category = await admin_catalog_service.delete_category(session, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return CategorySchema.model_validate(category)


@router.get("/tags", response_model=PaginatedResponse[TagSchema])
async def list_tags(
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100, alias="perPage"),
):
    tags, total = await admin_catalog_service.list_tags(session, page, per_page)
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    return PaginatedResponse[TagSchema](
        data=[TagSchema.model_validate(tag) for tag in tags],
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


@router.post("/tags", response_model=TagSchema)
async def create_tag(
    payload: TagCreateSchema,
    session: AsyncSession = Depends(get_session),
):
    tag = await admin_catalog_service.create_tag(session, payload.model_dump())
    return TagSchema.model_validate(tag)


@router.patch("/tags/{tag_id}", response_model=TagSchema)
async def update_tag(
    tag_id: str,
    payload: TagUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    tag = await admin_catalog_service.update_tag(session, tag_id, payload.model_dump())
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return TagSchema.model_validate(tag)


@router.delete("/tags/{tag_id}", response_model=TagSchema)
async def delete_tag(
    tag_id: str,
    session: AsyncSession = Depends(get_session),
):
    tag = await admin_catalog_service.delete_tag(session, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return TagSchema.model_validate(tag)


@router.get("/items", response_model=PaginatedResponse[ItemListSchema])
async def list_items(
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None, alias="isActive"),
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100, alias="perPage"),
):
    items, total = await admin_catalog_service.list_items(
        session, q, is_active, category, tag, page, per_page
    )
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    return PaginatedResponse[ItemListSchema](
        data=[
            ItemListSchema(
                id=str(item.id),
                slug=item.slug,
                title=item.title,
                short_description=None,
                is_active=item.is_active,
                main_image_url=None,
                min_price_rub=item.min_price_rub,
                max_price_rub=item.max_price_rub,
                has_stock=item.has_stock,
                category_slugs=[],
                tag_slugs=[],
            )
            for item in items
        ],
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


@router.post("/items", response_model=ItemListSchema)
async def create_item(
    payload: ItemCreateSchema,
    session: AsyncSession = Depends(get_session),
):
    item = await admin_catalog_service.create_item(session, payload.model_dump())
    return ItemListSchema(
        id=str(item.id),
        slug=item.slug,
        title=item.title,
        short_description=None,
        is_active=item.is_active,
        main_image_url=None,
        min_price_rub=item.min_price_rub,
        max_price_rub=item.max_price_rub,
        has_stock=item.has_stock,
        category_slugs=[],
        tag_slugs=[],
    )


@router.patch("/items/{item_id}", response_model=ItemListSchema)
async def update_item(
    item_id: str,
    payload: ItemUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    item = await admin_catalog_service.update_item(session, item_id, payload.model_dump())
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ItemListSchema(
        id=str(item.id),
        slug=item.slug,
        title=item.title,
        short_description=None,
        is_active=item.is_active,
        main_image_url=None,
        min_price_rub=item.min_price_rub,
        max_price_rub=item.max_price_rub,
        has_stock=item.has_stock,
        category_slugs=[],
        tag_slugs=[],
    )


@router.delete("/items/{item_id}", response_model=ItemListSchema)
async def delete_item(
    item_id: str,
    session: AsyncSession = Depends(get_session),
):
    item = await admin_catalog_service.delete_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ItemListSchema(
        id=str(item.id),
        slug=item.slug,
        title=item.title,
        short_description=None,
        is_active=item.is_active,
        main_image_url=None,
        min_price_rub=item.min_price_rub,
        max_price_rub=item.max_price_rub,
        has_stock=item.has_stock,
        category_slugs=[],
        tag_slugs=[],
    )


@router.post("/items/{item_id}/images", response_model=ItemImageSchema)
async def create_item_image(
    item_id: str,
    payload: ItemImageCreateSchema,
    session: AsyncSession = Depends(get_session),
):
    image = await admin_catalog_service.create_item_image(
        session, item_id, payload.model_dump()
    )
    return ItemImageSchema.model_validate(image)


@router.patch("/images/{image_id}", response_model=ItemImageSchema)
async def update_item_image(
    image_id: str,
    payload: ItemImageUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    image = await admin_catalog_service.update_item_image(
        session, image_id, payload.model_dump()
    )
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ItemImageSchema.model_validate(image)


@router.delete("/images/{image_id}", response_model=ItemImageSchema)
async def delete_item_image(
    image_id: str,
    session: AsyncSession = Depends(get_session),
):
    image = await admin_catalog_service.delete_item_image(session, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ItemImageSchema.model_validate(image)


@router.post("/items/{item_id}/variants", response_model=VariantSchema)
async def create_variant(
    item_id: str,
    payload: VariantCreateSchema,
    session: AsyncSession = Depends(get_session),
):
    variant = await admin_catalog_service.create_variant(session, item_id, payload.model_dump())
    return VariantSchema.model_validate(variant)


@router.patch("/variants/{variant_id}", response_model=VariantSchema)
async def update_variant(
    variant_id: str,
    payload: VariantUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    variant = await admin_catalog_service.update_variant(session, variant_id, payload.model_dump())
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return VariantSchema.model_validate(variant)


@router.delete("/variants/{variant_id}", response_model=VariantSchema)
async def delete_variant(
    variant_id: str,
    session: AsyncSession = Depends(get_session),
):
    variant = await admin_catalog_service.delete_variant(session, variant_id)
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return VariantSchema.model_validate(variant)
