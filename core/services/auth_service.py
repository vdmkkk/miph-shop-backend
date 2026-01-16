from __future__ import annotations

import hashlib
import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import create_access_token
from core.config import settings
from core.models.user import AuthMagicToken, AuthRefreshToken, User

MAGIC_TOKEN_TTL_MINUTES = 15
MAGIC_RATE_LIMIT_SECONDS = 60

_magic_rate_limit: dict[str, datetime] = defaultdict(
    lambda: datetime.min.replace(tzinfo=timezone.utc)
)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(f"{raw_token}{settings.jwt_secret}".encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _is_rate_limited(key: str) -> bool:
    last_sent = _magic_rate_limit[key]
    return (last_sent + timedelta(seconds=MAGIC_RATE_LIMIT_SECONDS)) > _now()


def _mark_rate_limited(key: str) -> None:
    _magic_rate_limit[key] = _now()


async def request_magic_link(
    session: AsyncSession,
    email: str,
    flow_context: dict[str, Any] | None,
    cart_snapshot: dict[str, Any] | None,
    client_key: str,
) -> str:
    if _is_rate_limited(client_key):
        return ""

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = _now() + timedelta(minutes=MAGIC_TOKEN_TTL_MINUTES)

    session.add(
        AuthMagicToken(
            email=email,
            token_hash=token_hash,
            expires_at=expires_at,
            flow_context=flow_context,
            cart_snapshot=cart_snapshot,
        )
    )
    await session.commit()
    _mark_rate_limited(client_key)
    return raw_token


async def consume_magic_link(
    session: AsyncSession,
    raw_token: str,
    profile: dict[str, Any] | None,
) -> tuple[User | None, dict[str, Any] | None, bool]:
    token_hash = _hash_token(raw_token)
    token_row = await session.scalar(
        select(AuthMagicToken)
        .where(AuthMagicToken.token_hash == token_hash)
        .where(AuthMagicToken.consumed_at.is_(None))
        .where(AuthMagicToken.expires_at > _now())
    )

    if token_row is None:
        return None, None, False

    email = token_row.email
    user = await session.scalar(select(User).where(User.email == email))

    if user is None and profile is None:
        return None, token_row.flow_context, True

    if user is None:
        user = User(
            email=email,
            name=profile["name"],
            phone=profile["phone"],
            is_active=True,
        )
        session.add(user)

    user.last_login_at = _now()
    token_row.consumed_at = _now()
    await session.commit()
    return user, token_row.flow_context, False


async def create_refresh_token(
    session: AsyncSession, user: User, user_agent: str | None, ip: str | None
) -> str:
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = _now() + timedelta(days=settings.refresh_token_ttl_days)

    session.add(
        AuthRefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
    )
    await session.commit()
    return raw_token


async def rotate_refresh_token(
    session: AsyncSession, raw_token: str
) -> tuple[str, User] | None:
    token_hash = _hash_token(raw_token)
    token_row = await session.scalar(
        select(AuthRefreshToken)
        .where(AuthRefreshToken.token_hash == token_hash)
        .where(AuthRefreshToken.revoked_at.is_(None))
        .where(AuthRefreshToken.expires_at > _now())
    )
    if token_row is None:
        return None

    token_row.revoked_at = _now()
    await session.flush()

    user = await session.scalar(select(User).where(User.id == token_row.user_id))
    if user is None:
        return None

    new_token = await create_refresh_token(
        session, user, token_row.user_agent, token_row.ip
    )
    return new_token, user


async def revoke_refresh_token(session: AsyncSession, raw_token: str) -> None:
    token_hash = _hash_token(raw_token)
    await session.execute(
        update(AuthRefreshToken)
        .where(AuthRefreshToken.token_hash == token_hash)
        .where(AuthRefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    await session.commit()


def create_access_token_for_user(user: User) -> str:
    return create_access_token(
        subject=str(user.id),
        expires_in_seconds=settings.access_token_ttl_seconds,
    )
