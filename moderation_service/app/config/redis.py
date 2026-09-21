"""Client Redis asyncio (BullMQ + SpamFilter) et vérification de dépendance."""

from __future__ import annotations

import asyncio

import redis.asyncio as aioredis

from app.config.settings import Settings


def create_redis(settings: Settings) -> aioredis.Redis:
    """Construit le client `redis.asyncio.Redis` depuis la configuration."""
    url = f"redis://{settings.redis_host}:{settings.redis_port}"
    return aioredis.from_url(
        url,
        password=settings.redis_password or None,
        decode_responses=True,
    )


async def check_redis(client: aioredis.Redis, timeout_sec: float = 2.0) -> bool:
    """PING Redis ; True si joignable, False sinon (aucune exception ne sort)."""
    try:
        return bool(await asyncio.wait_for(client.ping(), timeout=timeout_sec))
    except Exception:
        return False


__all__ = ["create_redis", "check_redis"]
