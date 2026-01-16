import logging
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from apps.public_api.routers import auth, cart, catalog, likes, me, orders
from core.errors import (
    db_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from core.logging_utils import setup_logging
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("app.public")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[public] start {request.method} {request.url.path}", flush=True)
    logger.info("Request start %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        print(
            f"[public] end {request.method} {request.url.path} -> {response.status_code}",
            flush=True,
        )
        logger.info("Request end %s %s -> %s", request.method, request.url.path, response.status_code)
        return response
    except Exception:
        print(f"[public] error {request.method} {request.url.path}", flush=True)
        print(traceback.format_exc(), flush=True)
        logger.exception("Unhandled request error %s %s", request.method, request.url.path)
        raise


@app.get("/api/v1/health")
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


app.include_router(auth.router)
app.include_router(me.router)
app.include_router(cart.router)
app.include_router(catalog.router)
app.include_router(likes.router)
app.include_router(orders.router)
