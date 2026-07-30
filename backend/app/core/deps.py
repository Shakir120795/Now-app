"""Shared FastAPI dependencies: current principal + RBAC guards."""
from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_token
from app.db.session import get_db
from app.features.auth.models import User
from app.features.auth.repository import AuthRepository


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise Unauthorized("Missing bearer token.")
    return header.removeprefix("Bearer ").strip()


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    token = _extract_bearer(request)
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Access token expired.")
    except jwt.PyJWTError:
        raise Unauthorized("Invalid access token.")
    if payload.get("type") != "access":
        raise Unauthorized("Wrong token type.")
    user = await AuthRepository(db).get_user_by_id(uuid.UUID(payload["sub"]))
    if user is None or user.status != "active":
        raise Unauthorized("User not found or inactive.")
    return user


async def get_current_customer(user: User = Depends(get_current_user)) -> User:
    if user.is_guest:
        raise Forbidden("This action requires a registered account.")
    return user


def require_permission(code: str):
    """Dependency ensuring the current user holds the given RBAC permission."""

    async def _dep(user: User = Depends(get_current_user)) -> User:
        held = {p.code for role in user.roles for p in role.permissions}
        if code not in held and "*" not in held:
            raise Forbidden(f"Missing permission: {code}")
        return user

    return _dep
