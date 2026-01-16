from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.config import settings
from core.db import get_session
from core.models.user import User
from core.schemas import ErrorDetails, ErrorResponse, OrderResponse, OrderSchema, PaginatedResponse
from core.services import order_service

router = APIRouter(prefix="/api/v1/me/orders", tags=["orders"])


class DeliveryPayload(BaseModel):
    method: str
    address: dict[str, Any]


class ContactPayload(BaseModel):
    name: str
    phone: str
    email: str


class CreateOrderPayload(BaseModel):
    delivery: DeliveryPayload
    contact: ContactPayload
    comment: str | None = None


def _error(code: str, message: str, status_code: int, details: dict | None = None):
    payload = ErrorResponse(error=ErrorDetails(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=payload.model_dump(by_alias=True))


@router.post("", response_model=OrderResponse)
async def create_order(
    payload: CreateOrderPayload,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    order, errors = await order_service.create_order_from_cart(
        session,
        user_id=str(user.id),
        delivery_method=payload.delivery.method,
        delivery_address=payload.delivery.address,
        contact=payload.contact.model_dump(),
        comment=payload.comment,
    )
    if order is None:
        if errors and errors[0]["code"] == "CART_EMPTY":
            return _error("CART_EMPTY", "Cart is empty", status.HTTP_400_BAD_REQUEST)
        if errors and errors[0]["code"] == "OUT_OF_STOCK":
            return _error(
                "OUT_OF_STOCK",
                "Some items are out of stock",
                status.HTTP_400_BAD_REQUEST,
                details={"variants": errors[0].get("variants", [])},
            )
        return _error(
            "ORDER_CREATE_FAILED",
            "Unable to create order",
            status.HTTP_400_BAD_REQUEST,
        )
    return {"order": order}


@router.get("", response_model=PaginatedResponse[OrderSchema])
async def list_orders(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100, alias="perPage"),
):
    orders, total = await order_service.list_orders(
        session, user_id=str(user.id), page=page, per_page=per_page
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
    user: User = Depends(get_current_user),
):
    order = await order_service.get_order(session, user_id=str(user.id), order_id=order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"order": order}


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    order = await order_service.cancel_order(session, user_id=str(user.id), order_id=order_id)
    if order is None:
        return _error(
            "ORDER_NOT_FOUND",
            "Order not found or cannot cancel",
            status.HTTP_400_BAD_REQUEST,
        )
    return {"order": order}


@router.post("/{order_id}/simulate-payment", response_model=OrderResponse)
async def simulate_payment(
    order_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not settings.enable_dev_endpoints:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    order = await order_service.simulate_payment(
        session, user_id=str(user.id), order_id=order_id
    )
    if order is None:
        return _error(
            "ORDER_NOT_FOUND",
            "Order not found or cannot pay",
            status.HTTP_400_BAD_REQUEST,
        )
    return {"order": order}
