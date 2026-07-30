"""Redis fixed-window rate limiter, usable as a FastAPI dependency factory."""
from __future__ import annotations

from fastapi import Request

from app.core.errors import RateLimited
from app.core.redis import redis_client


async def enforce_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    """Increment a window counter; raise RateLimited when the limit is exceeded."""
    bucket = f"rl:{key}"
    count = await redis_client.incr(bucket)
    if count == 1:
        await redis_client.expire(bucket, window_seconds)
    if count > limit:
        raise RateLimited("Too many requests. Please try again later.")


def rate_limit(prefix: str, limit: int, window_seconds: int):
    """Dependency that limits by client IP under the given prefix."""

    async def _dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        await enforce_rate_limit(f"{prefix}:{ip}", limit, window_seconds)

    return _dep
