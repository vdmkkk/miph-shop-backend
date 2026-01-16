from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.admin_api.routers import catalog, orders, users
from core.errors import http_exception_handler

app = FastAPI(title="Admin API", openapi_url="/admin/v1/openapi.json")


@app.get("/admin/v1/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return http_exception_handler(request, exc)


app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(users.router)
