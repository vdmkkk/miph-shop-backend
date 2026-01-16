from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import (
    ErrorDetails,
    ErrorResponse,
    MagicConsumeRequest,
    MagicConsumeResponse,
    MagicLinkRequest,
    OkResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserSchema,
)
from core.services import auth_service, mail_service
from core.db import get_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _error(code: str, message: str, status_code: int, details: dict | None = None):
    payload = ErrorResponse(error=ErrorDetails(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=payload.model_dump(by_alias=True))


@router.post("/magic/request", response_model=OkResponse)
async def request_magic_link(
    payload: MagicLinkRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    client_key = f"{client_ip}:{email}"
    raw_token = await auth_service.request_magic_link(
        session=session,
        email=email,
        flow_context=payload.flow_context,
        cart_snapshot=payload.cart_snapshot,
        client_key=client_key,
    )
    if raw_token:
        mail_service.send_magic_link(email, raw_token)
    return OkResponse()


@router.post("/magic/consume", response_model=MagicConsumeResponse)
async def consume_magic_link(
    payload: MagicConsumeRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user, flow_context, profile_required = await auth_service.consume_magic_link(
        session=session,
        raw_token=payload.token,
        profile=payload.profile.model_dump() if payload.profile else None,
    )

    if profile_required:
        payload = ErrorResponse(
            error=ErrorDetails(
                code="PROFILE_REQUIRED",
                message="Please complete profile to finish signup",
                details={"requiredFields": ["name", "phone"]},
            )
        ).model_dump(by_alias=True)
        payload["flowContext"] = flow_context
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload)

    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    if not user.is_active:
        return _error(code="USER_DISABLED", message="User disabled", status_code=403)

    access_token = auth_service.create_access_token_for_user(user)
    refresh_token = await auth_service.create_refresh_token(
        session,
        user,
        request.headers.get("User-Agent"),
        request.client.host if request.client else None,
    )

    cart_payload = None
    if payload.merge_cart:
        if payload.merge_cart.mode not in {"add", "replace", "max"}:
            raise HTTPException(status_code=400, detail="Invalid merge mode")
        from core.services import cart_service

        cart_payload, _warnings = await cart_service.merge_cart(
            session,
            user_id=str(user.id),
            mode=payload.merge_cart.mode,
            items=[item.model_dump(by_alias=True) for item in payload.merge_cart.items],
        )

    return MagicConsumeResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserSchema.model_validate(user),
        flow_context=flow_context,
        cart=cart_payload,
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
):
    rotated = await auth_service.rotate_refresh_token(session, payload.refresh_token)
    if rotated is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    new_token, user = rotated

    access_token = auth_service.create_access_token_for_user(user)
    return RefreshTokenResponse(access_token=access_token, refresh_token=new_token)


@router.post("/logout", response_model=OkResponse)
async def logout(
    payload: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
):
    await auth_service.revoke_refresh_token(session, payload.refresh_token)
    return OkResponse()
