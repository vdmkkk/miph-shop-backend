from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.user import User


async def list_users(
    session: AsyncSession,
    q: str | None,
    is_active: bool | None,
    page: int,
    per_page: int,
) -> tuple[list[User], int]:
    stmt = select(User)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(User.email).like(like) | func.lower(User.name).like(like)
        )
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt) or 0
    rows = await session.scalars(
        stmt.order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return list(rows), total


async def update_user(
    session: AsyncSession, user_id: str, is_active: bool
) -> User | None:
    user_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(user_id)
    user = await session.scalar(select(User).where(User.id == user_uuid))
    if user is None:
        return None
    user.is_active = is_active
    await session.commit()
    await session.refresh(user)
    return user
