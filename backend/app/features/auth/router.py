"""Auth transport layer."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.features.auth.models import User
from app.features.auth.schemas import (
    GuestOut,
    OtpRequestIn,
    OtpRequestOut,
    OtpVerifyIn,
    RefreshIn,
    TokenPair,
    UserOut,
)
from app.features.auth.service import AuthService, _user_out

router = APIRouter(prefix="/auth", tags=["auth"])


def _meta(request: Request) -> dict:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
    }


@router.post("/otp/request", response_model=OtpRequestOut)
async def request_otp(body: OtpRequestIn, request: Request, db: AsyncSession = Depends(get_db)):
    rid, ttl = await AuthService(db).request_otp(body.phone, _meta(request)["ip"])
    return OtpRequestOut(request_id=rid, expires_in=ttl)


@router.post("/otp/verify", response_model=TokenPair)
async def verify_otp(body: OtpVerifyIn, request: Request, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).verify_otp(body.phone, body.code, body.guest_token, _meta(request))


@router.post("/guest", response_model=GuestOut)
async def guest_login(request: Request, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).guest_login(_meta(request))


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshIn, request: Request, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).refresh(body.refresh_token, _meta(request))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    await AuthService(db).logout(body.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await AuthService(db).logout_all(user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return _user_out(user)
