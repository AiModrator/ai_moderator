"""Tests d'intégration du `/health` avec MongoDB réel (Tâche 01)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.health import router as health_router
from app.config.settings import Settings
from app.db import check_mongo, create_mongo_client, get_database


def _app(settings: Settings) -> FastAPI:
    mongo_client = create_mongo_client(settings)
    db = get_database(mongo_client, settings)
    app = FastAPI()
    app.state.settings = settings
    app.state.mongo_client = mongo_client
    app.state.db = db
    app.include_router(health_router)
    return app


@pytest.mark.integration
async def test_health_ok(settings: Settings) -> None:
    app = _app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        response = await http_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mongo"] is True
    assert set(body["providers"]) == {"openrouter", "test"}
    mongo_client = app.state.mongo_client
    mongo_client.close()


@pytest.mark.integration
async def test_health_503_when_mongo_down() -> None:
    settings = Settings(
        encryption_key="a" * 44,
        gateway_api_key="g",
        admin_api_key="a",
        mongodb_uri="mongodb://127.0.0.1:27018",  # port non écouté
        mongodb_db="ai_gateway_test",
        log_format="console",
    )
    mongo_client = create_mongo_client(settings)
    db = get_database(mongo_client, settings)
    app = FastAPI()
    app.state.mongo_client = mongo_client
    app.state.db = db
    app.include_router(health_router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        response = await http_client.get("/health")
    mongo_client.close()
    assert response.status_code == 503
    assert response.json()["mongo"] is False


@pytest.mark.integration
async def test_check_mongo_real(settings: Settings) -> None:
    mongo_client = create_mongo_client(settings)
    ok = await check_mongo(mongo_client)
    assert ok is True
    mongo_client.close()
