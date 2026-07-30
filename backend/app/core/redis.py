"""Shared async Redis client."""
from __future__ import annotations

import redis.asyncio as redis

from app.core.config import settings

redis_client: redis.Redis = redis.from_url(
    settings.redis_url, encoding="utf-8", decode_responses=True
)


async def get_redis() -> redis.Redis:
    return redis_client
