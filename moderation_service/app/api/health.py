"""Endpoint de santé `GET /health` (main.md §12)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.config.redis import check_redis
from app.config.settings import Settings

PoolStatsProvider = Callable[[], dict]
GatewayCheck = Callable[[], Awaitable[bool]]


def build_health_router(
    settings: Settings,
    redis_client: Redis,
    pool_stats: PoolStatsProvider | None = None,
    gateway_check: GatewayCheck | None = None,
) -> APIRouter:
    """Construit le router `/health`.

    - `pool_stats` : fournit `{capacity, active, waiting, paused}` (WorkerPool,
      branché en tâche 07/08) — `None` tant que le pool n'est pas démarré.
    - `gateway_check` : vérification async de l'AI Gateway (phase 4/5) —
      `None` → `aiGateway: false`.
    """

    router = APIRouter()

    @router.get("/health", tags=["health"])
    async def health() -> JSONResponse:
        redis_ok = await check_redis(redis_client)
        pool = pool_stats() if pool_stats else {}
        gateway_ok = bool(await gateway_check()) if gateway_check else False
        body = {
            "status": "ok" if redis_ok else "degraded",
            "redis": redis_ok,
            "aiGateway": gateway_ok,
            "pool": {
                "capacity": pool.get("capacity"),
                "active": pool.get("active"),
                "waiting": pool.get("waiting"),
                "paused": pool.get("paused"),
            },
            "cpu": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent,
        }
        return JSONResponse(status_code=200 if redis_ok else 503, content=body)

    return router


__all__ = ["build_health_router"]
