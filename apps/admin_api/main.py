from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.admin_api.routers import catalog, orders, users
from core.errors import http_exception_handler

app = FastAPI(
    title="MIPH Shop Admin API",
    openapi_url="/admin/v1/openapi.json",
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


@app.get("/admin/v1/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return http_exception_handler(request, exc)


app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(users.router)
