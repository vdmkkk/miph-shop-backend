from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.public_api.routers import auth, cart, catalog, likes, me, orders
from core.errors import http_exception_handler

app = FastAPI(title="Public API", openapi_url="/api/v1/openapi.json")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return http_exception_handler(request, exc)


app.include_router(auth.router)
app.include_router(me.router)
app.include_router(cart.router)
app.include_router(catalog.router)
app.include_router(likes.router)
app.include_router(orders.router)
