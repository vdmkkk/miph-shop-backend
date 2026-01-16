from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.db import get_session
from core.models.user import User
from core.schemas import CartMergeResponse, CartResponse, MergeCartPayload
from core.services import cart_service

router = APIRouter(prefix="/api/v1/me/cart", tags=["cart"])


class CartQtyRequest(BaseModel):
    qty: int = Field(ge=1)


@router.get("", response_model=CartResponse)
async def get_cart(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    cart = await cart_service.build_cart_schema(session, str(user.id))
    return {"cart": cart}


@router.post("/merge", response_model=CartMergeResponse)
async def merge_cart(
    payload: MergeCartPayload,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if payload.mode not in {"add", "replace", "max"}:
        raise HTTPException(status_code=400, detail="Invalid merge mode")
    cart, warnings = await cart_service.merge_cart(
        session,
        user_id=str(user.id),
        mode=payload.mode,
        items=[item.model_dump(by_alias=True) for item in payload.items],
    )
    return {
        "cart": cart,
        "merge_warnings": [
            {"variant_id": warning.variant_id, "reason": warning.reason}
            for warning in warnings
        ],
    }


@router.put("/items/{variant_id}", response_model=CartResponse)
async def update_cart_item(
    variant_id: str,
    payload: CartQtyRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    cart = await cart_service.update_cart_item(
        session, user_id=str(user.id), variant_id=variant_id, qty=payload.qty
    )
    return {"cart": cart}


@router.delete("/items/{variant_id}", response_model=CartResponse)
async def delete_cart_item(
    variant_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    cart = await cart_service.delete_cart_item(
        session, user_id=str(user.id), variant_id=variant_id
    )
    return {"cart": cart}


@router.post("/clear", response_model=CartResponse)
async def clear_cart(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    cart = await cart_service.clear_cart(session, user_id=str(user.id))
    return {"cart": cart}
