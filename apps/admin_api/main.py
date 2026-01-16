import logging
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import SQLAlchemyError

from apps.admin_api.routers import catalog, orders, users
from core.errors import (
    db_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from core.logging_utils import setup_logging
from core.migrations import run_migrations

app = FastAPI(
    title="MIPH Shop Admin API",
    openapi_url="/admin/v1/openapi.json",
    docs_url="/admin/v1/docs",
    redoc_url="/admin/v1/redoc",
    description=(
        "Administrative API for managing the MIPH shop catalog and orders.\n\n"
        "## Authentication\n"
        "- All endpoints require `X-Admin-Api-Key` header.\n\n"
        "## Conventions\n"
        "- Base path: `/admin/v1`\n"
        "- JSON: camelCase\n"
        "- Pagination: `page`, `perPage` with `total` and `totalPages`\n"
        "- Soft deletes: catalog entities are disabled via `isActive=false`\n"
    ),
    contact={
        "name": "MIPH Shop Backend",
        "url": "http://localhost",
    },
    license_info={"name": "Educational use"},
    openapi_tags=[
        {
            "name": "admin-catalog",
            "description": (
                "Catalog management: categories, tags, items, images, and variants. "
                "Includes required side effects for variant stats recalculation."
            ),
        },
        {
            "name": "admin-orders",
            "description": (
                "Order management: list, view, and change status with event history."
            ),
        },
        {
            "name": "admin-users",
            "description": "User management: list users and toggle active status.",
        },
    ],
)

logger = logging.getLogger("app.admin")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[admin] start {request.method} {request.url.path}", flush=True)
    logger.info("Request start %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        print(
            f"[admin] end {request.method} {request.url.path} -> {response.status_code}",
            flush=True,
        )
        logger.info("Request end %s %s -> %s", request.method, request.url.path, response.status_code)
        return response
    except Exception:
        print(f"[admin] error {request.method} {request.url.path}", flush=True)
        print(traceback.format_exc(), flush=True)
        logger.exception("Unhandled request error %s %s", request.method, request.url.path)
        raise


def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})[
        "AdminApiKey"
    ] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-Admin-Api-Key",
        "description": "Admin API key required for all admin endpoints.",
    }
    schema["security"] = [{"AdminApiKey": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _custom_openapi


@app.get("/admin/v1/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return http_exception_handler(request, exc)


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    return db_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return validation_exception_handler(request, exc)


@app.exception_handler(ResponseValidationError)
async def response_validation_handler(
    request: Request, exc: ResponseValidationError
) -> JSONResponse:
    return validation_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return unhandled_exception_handler(request, exc)


@app.on_event("startup")
async def run_startup_migrations() -> None:
    setup_logging()
    await run_in_threadpool(run_migrations)


app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(users.router)
