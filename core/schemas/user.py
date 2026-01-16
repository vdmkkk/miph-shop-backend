from __future__ import annotations

from datetime import datetime

from core.schemas.base import CamelModel


class UserSchema(CamelModel):
    id: str
    email: str
    name: str
    phone: str | None
    is_active: bool
    created_at: datetime


class UserUpdateSchema(CamelModel):
    name: str | None = None
    phone: str | None = None


class UserResponse(CamelModel):
    user: UserSchema
