"""Comportement au bootstrap (main.md §12.2) : Redis KO → exit 1, gateway KO → warning.

Redis réel pour le cas « OK » ; port injoignable pour « KO » ; gateway simulée
`respx`. Vérifie aussi le câblage `pool.stats` / `gateway.health` dans `/health`.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config.logging import get_logger
from app.config.redis import check_redis, create_redis
from app.config.settings import Settings
from main import build_gateway, build_lexicon_repository, build_pool, create_app, resolve_dependencies

GATEWAY = "http://gateway"


def _settings(**overrides) -> Settings:
    base = dict(test_queue_prefix="test", log_format="console", ai_gateway_url=GATEWAY)
    base.update(overrides)
    return Settings(**base)


@pytest.mark.integration
async def test_redis_unreachable_exits_1() -> None:
    settings = _settings(redis_host="127.0.0.1", redis_port=6399)
    client = create_redis(settings)
    redis_ok = await check_redis(client)
    await client.aclose()
    assert redis_ok is False
    with pytest.raises(SystemExit) as excinfo:
        resolve_dependencies(False, True, get_logger())
    assert excinfo.value.code == 1


@pytest.mark.integration
@respx.mock
async def test_gateway_unreachable_warns_but_boots() -> None:
    settings = _settings()
    respx.get(f"{GATEWAY}/health").mock(return_value=httpx.Response(503, json={"status": "ko"}))
    gateway = build_gateway(settings)
    try:
        gateway_ok = await gateway.health()
    finally:
        await gateway.aclose()
    assert gateway_ok is False
    resolve_dependencies(True, gateway_ok, get_logger())  # ne lève pas


@pytest.mark.integration
async def test_both_dependencies_ok() -> None:
    settings = _settings()
    client = create_redis(settings)
    redis_ok = await check_redis(client)
    await client.aclose()
    assert redis_ok is True
    resolve_dependencies(True, True, get_logger())  # ne lève pas


@pytest.mark.integration
@respx.mock
async def test_create_app_wires_pool_and_gateway() -> None:
    settings = _settings(monitor_interval_sec=3600)
    respx.get(f"{GATEWAY}/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    redis_client = create_redis(settings)
    gateway = build_gateway(settings)
    lexicon = build_lexicon_repository()
    lexicon.load()
    pool = build_pool(settings, redis_client=redis_client, gateway=gateway, lexicon=lexicon)
    try:
        app = create_app(settings, redis_client=redis_client, pool=pool, gateway=gateway)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["redis"] is True
        assert body["aiGateway"] is True
        assert set(body["pool"]) == {"capacity", "active", "waiting", "paused"}
        assert isinstance(app, FastAPI)
    finally:
        await pool.worker.close(force=True)
        await gateway.aclose()
        await redis_client.aclose()
