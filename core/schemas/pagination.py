from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import Field

from core.schemas.base import CamelModel

T = TypeVar("T")


class DataResponse(CamelModel, Generic[T]):
    data: list[T]


class PaginatedResponse(CamelModel, Generic[T]):
    data: list[T]
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1)
    total: int
    total_pages: int
