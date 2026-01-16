from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from apps.admin_api.routers import catalog, orders, users
from core.errors import http_exception_handler
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


@app.on_event("startup")
async def run_startup_migrations() -> None:
    await run_in_threadpool(run_migrations)


app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(users.router)
