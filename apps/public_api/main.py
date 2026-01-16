from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from apps.public_api.routers import auth, cart, catalog, likes, me, orders
from core.errors import http_exception_handler
from core.migrations import run_migrations

app = FastAPI(
    title="MIPH Shop Public API",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    description=(
        "Public-facing API for the MIPH educational shop backend.\n\n"
        "## Highlights\n"
        "- Magic-link authentication (no passwords)\n"
        "- Catalog browsing with filters and pagination\n"
        "- Likes, cart sync, and checkout flows\n"
        "- Consistent error envelope `{ error: { code, message, details } }`\n\n"
        "## Conventions\n"
        "- Base path: `/api/v1`\n"
        "- JSON: camelCase\n"
        "- Monetary fields are floats (RUB) in API responses\n"
        "- Pagination: `page`, `perPage` with `total` and `totalPages`\n"
    ),
    contact={
        "name": "MIPH Shop Backend",
        "url": "http://localhost",
    },
    license_info={"name": "Educational use"},
    openapi_tags=[
        {
            "name": "auth",
            "description": (
                "Magic-link authentication workflow: request link, consume token, "
                "refresh access token, and logout."
            ),
        },
        {
            "name": "me",
            "description": "User profile endpoints for the currently authenticated user.",
        },
        {
            "name": "catalog",
            "description": (
                "Public catalog endpoints: categories, tags, items list, item details."
            ),
        },
        {
            "name": "likes",
            "description": "Wishlist-like endpoints for adding/removing liked items.",
        },
        {
            "name": "cart",
            "description": (
                "Server-side cart endpoints for authenticated users, including cart "
                "merge after login."
            ),
        },
        {
            "name": "orders",
            "description": (
                "Checkout and order history: create order from cart, list orders, "
                "view order details, cancel, and simulate payment (dev-only)."
            ),
        },
    ],
)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return http_exception_handler(request, exc)


@app.on_event("startup")
async def run_startup_migrations() -> None:
    await run_in_threadpool(run_migrations)


app.include_router(auth.router)
app.include_router(me.router)
app.include_router(cart.router)
app.include_router(catalog.router)
app.include_router(likes.router)
app.include_router(orders.router)
