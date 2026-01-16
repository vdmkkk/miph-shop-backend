from __future__ import annotations

from typing import Any

from pydantic import Field

from core.schemas.base import CamelModel
from core.schemas.cart import CartSchema
from core.schemas.user import UserSchema


class MagicLinkRequest(CamelModel):
    email: str
    flow_context: dict[str, Any] | None = None
    cart_snapshot: dict[str, Any] | None = None


class ProfilePayload(CamelModel):
    name: str
    phone: str


class MergeCartItem(CamelModel):
    variant_id: str
    qty: int = Field(ge=1)


class MergeCartPayload(CamelModel):
    mode: str
    items: list[MergeCartItem]


class MagicConsumeRequest(CamelModel):
    token: str
    profile: ProfilePayload | None = None
    merge_cart: MergeCartPayload | None = None


class MagicConsumeResponse(CamelModel):
    access_token: str
    refresh_token: str
    user: UserSchema
    flow_context: dict[str, Any] | None = None
    cart: CartSchema | None = None


class RefreshTokenRequest(CamelModel):
    refresh_token: str


class RefreshTokenResponse(CamelModel):
    access_token: str
    refresh_token: str


class LogoutRequest(CamelModel):
    refresh_token: str


class OkResponse(CamelModel):
    ok: bool = True
