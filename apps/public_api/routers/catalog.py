from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.schemas import (
    CategoryListResponse,
    ItemDetailResponse,
    ItemListSchema,
    PaginatedResponse,
    TagListResponse,
)
from core.services import catalog_service

router = APIRouter(prefix="/api/v1", tags=["catalog"])


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(session: AsyncSession = Depends(get_session)):
    categories = await catalog_service.list_categories(session)
    return {"data": categories}


@router.get("/tags", response_model=TagListResponse)
async def list_tags(session: AsyncSession = Depends(get_session)):
    tags = await catalog_service.list_tags(session)
    return {"data": tags}


@router.get("/items", response_model=PaginatedResponse[ItemListSchema])
async def list_items(
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    tags: str | None = Query(default=None),
    price_min_rub: Decimal | None = Query(default=None, alias="priceMinRub"),
    price_max_rub: Decimal | None = Query(default=None, alias="priceMaxRub"),
    in_stock: bool | None = Query(default=None, alias="inStock"),
    sort: str | None = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100, alias="perPage"),
):
    tag_list = tags.split(",") if tags else None
    items, total = await catalog_service.list_items(
        session,
        q=q,
        category=category,
        tags=tag_list,
        price_min=price_min_rub,
        price_max=price_max_rub,
        in_stock=in_stock,
        sort=sort,
        page=page,
        per_page=per_page,
    )
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    return PaginatedResponse[ItemListSchema](
        data=items,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


@router.get("/items/{slug}", response_model=ItemDetailResponse)
async def get_item_detail(
    slug: str, session: AsyncSession = Depends(get_session)
):
    item = await catalog_service.get_item_detail(session, slug)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"item": item}
