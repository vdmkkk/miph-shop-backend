from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.db import get_session
from core.models.catalog import Item
from core.models.like import Like
from core.models.user import User
from core.schemas import ItemListSchema, PaginatedResponse
from core.services import catalog_service

router = APIRouter(prefix="/api/v1/me/likes", tags=["likes"])


def _to_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id") from exc


@router.get("", response_model=PaginatedResponse[ItemListSchema])
async def list_likes(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100, alias="perPage"),
):
    items, total = await catalog_service.list_liked_items(
        session, user_id=str(user.id), page=page, per_page=per_page
    )
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    return PaginatedResponse[ItemListSchema](
        data=items,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


@router.post("/{item_id}")
async def add_like(
    item_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item_uuid = _to_uuid(item_id)
    exists = await session.scalar(select(Item).where(Item.id == item_uuid))
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    like_exists = await session.scalar(
        select(Like).where(Like.user_id == user.id).where(Like.item_id == item_uuid)
    )
    if like_exists is None:
        session.add(Like(user_id=user.id, item_id=item_uuid))
        await session.commit()
    return {"ok": True}


@router.delete("/{item_id}")
async def delete_like(
    item_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item_uuid = _to_uuid(item_id)
    await session.execute(
        delete(Like).where(Like.user_id == user.id).where(Like.item_id == item_uuid)
    )
    await session.commit()
    return {"ok": True}
