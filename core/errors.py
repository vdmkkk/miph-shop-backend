from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.config import settings
from core.schemas import ErrorDetails, ErrorResponse

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("app.errors")


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


def db_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error", exc_info=exc)
    details = None
    if settings.enable_dev_endpoints:
        details = {"error": f"{exc.__class__.__name__}: {exc}"}
    if isinstance(exc, IntegrityError):
        payload = error_payload(
            code="CONFLICT", message="Database constraint violated", details=details
        )
        return JSONResponse(status_code=409, content=payload)
    payload = error_payload(code="DB_ERROR", message="Database error", details=details)
    return JSONResponse(status_code=400, content=payload)


def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    details = None
    if settings.enable_dev_endpoints:
        details = {"error": f"{exc.__class__.__name__}: {exc}"}
    payload = error_payload(
        code="INTERNAL_ERROR", message="Internal server error", details=details
    )
    return JSONResponse(status_code=500, content=payload)


def validation_exception_handler(
    request: Request, exc: RequestValidationError | ResponseValidationError
) -> JSONResponse:
    logger.exception("Validation error", exc_info=exc)
    payload = error_payload(
        code="VALIDATION_ERROR",
        message="Validation failed",
        details={"errors": exc.errors()},
    )
    return JSONResponse(status_code=422, content=payload)
