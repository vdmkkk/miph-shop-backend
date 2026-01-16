from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from core.schemas import ErrorDetails, ErrorResponse


def error_payload(code: str, message: str, details: dict | None = None) -> dict:
    return ErrorResponse(
        error=ErrorDetails(code=code, message=message, details=details)
    ).model_dump(by_alias=True)


def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        payload = exc.detail
    else:
        payload = error_payload(code="HTTP_ERROR", message=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=payload)
