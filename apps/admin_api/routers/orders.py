from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import require_admin
from core.db import get_session
from core.schemas import OrderResponse, OrderSchema, OrderStatusUpdateSchema, PaginatedResponse
from core.services import admin_order_service

router = APIRouter(prefix="/admin/v1/orders", tags=["admin-orders"], dependencies=[Depends(require_admin)])


@router.get("", response_model=PaginatedResponse[OrderSchema])
async def list_orders(
    session: AsyncSession = Depends(get_session),
    status: str | None = Query(default=None),
    email: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100, alias="perPage"),
):
    orders, total = await admin_order_service.list_orders(
        session, status, email, page, per_page
    )
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    return PaginatedResponse[OrderSchema](
        data=orders,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_session),
):
    order = await admin_order_service.get_order(session, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"order": order}


@router.post("/{order_id}/status", response_model=OrderResponse)
async def update_status(
    order_id: str,
    payload: OrderStatusUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    order = await admin_order_service.update_status(
        session, order_id, payload.to_status, payload.note
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"order": order}
