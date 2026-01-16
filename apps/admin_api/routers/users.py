from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import require_admin
from core.db import get_session
from core.schemas import PaginatedResponse, UserAdminUpdateSchema, UserSchema
from core.services import admin_user_service

router = APIRouter(prefix="/admin/v1/users", tags=["admin-users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=PaginatedResponse[UserSchema])
async def list_users(
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None, alias="isActive"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100, alias="perPage"),
):
    users, total = await admin_user_service.list_users(
        session, q, is_active, page, per_page
    )
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    return PaginatedResponse[UserSchema](
        data=[UserSchema.model_validate(user) for user in users],
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


@router.patch("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: str,
    payload: UserAdminUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    user = await admin_user_service.update_user(session, user_id, payload.is_active)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return UserSchema.model_validate(user)
