"""Tests d'intégration du `/health` avec Redis réel (Tâche 01)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.health import build_health_router
from app.config.redis import create_redis
from app.config.settings import Settings


def _app(settings: Settings, gateway_check=None) -> FastAPI:
    redis_client = create_redis(settings)
    app = FastAPI()
    app.include_router(build_health_router(settings, redis_client, gateway_check=gateway_check))
    return app


@pytest.mark.integration
async def test_health_ok(settings: Settings) -> None:
    app = _app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["redis"] is True
    assert body["status"] == "ok"
    assert body["aiGateway"] is False
    assert set(body["pool"]) == {"capacity", "active", "waiting", "paused"}


@pytest.mark.integration
async def test_health_503_when_redis_down() -> None:
    settings = Settings(test_queue_prefix="test", redis_host="127.0.0.1", redis_port=6399, redis_password="")
    redis_client = create_redis(settings)  # port non écouté → PING échoue
    app = FastAPI()
    app.include_router(build_health_router(settings, redis_client))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    await redis_client.aclose()
    assert response.status_code == 503
    assert response.json()["redis"] is False


@pytest.mark.integration
async def test_health_gateway_check(settings: Settings) -> None:
    async def fake_gateway_check() -> bool:
        return True

    app = _app(settings, gateway_check=fake_gateway_check)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.json()["aiGateway"] is True
