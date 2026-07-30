"""Application error types and the standard error envelope.

Every handled error serializes to:
    {"error": {"code","message","details","request_id"}}
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base domain error. Subclasses set code + http_status."""

    code = "internal_error"
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, details: list | None = None):
        self.message = message
        self.details = details or []
        super().__init__(message)


class BadRequest(AppError):
    code = "bad_request"
    http_status = status.HTTP_400_BAD_REQUEST


class Unauthorized(AppError):
    code = "unauthorized"
    http_status = status.HTTP_401_UNAUTHORIZED


class Forbidden(AppError):
    code = "forbidden"
    http_status = status.HTTP_403_FORBIDDEN


class NotFound(AppError):
    code = "not_found"
    http_status = status.HTTP_404_NOT_FOUND


class Conflict(AppError):
    code = "conflict"
    http_status = status.HTTP_409_CONFLICT


class RateLimited(AppError):
    code = "rate_limited"
    http_status = status.HTTP_429_TOO_MANY_REQUESTS


def _envelope(code: str, message: str, details: list) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": f"req_{uuid.uuid4().hex[:16]}",
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.http_status,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e["loc"][1:]), "issue": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("validation_error", "Request validation failed.", details),
        )
