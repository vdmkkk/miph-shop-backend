from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.db import get_session
from core.models.user import User
from core.schemas import UserResponse, UserSchema, UserUpdateSchema

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.get("", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return {"user": UserSchema.model_validate(user)}


@router.patch("", response_model=UserResponse)
async def update_me(
    payload: UserUpdateSchema,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if payload.name is not None:
        user.name = payload.name
    if payload.phone is not None:
        user.phone = payload.phone
    await session.commit()
    await session.refresh(user)
    return {"user": UserSchema.model_validate(user)}
