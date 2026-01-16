from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        json_encoders={
            Decimal: lambda value: float(value),
            UUID: lambda value: str(value),
        },
    )


class ErrorDetails(CamelModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(CamelModel):
    error: ErrorDetails
