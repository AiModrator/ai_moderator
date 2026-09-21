"""Fixtures partagées des tests du `moderation_service`."""

from __future__ import annotations

import pytest
from redis.asyncio import Redis

from app.config.redis import create_redis
from app.config.settings import Settings
from app.core.publisher import build_queue


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Settings de test : jamais de .env, Redis local réel pour integration/e2e."""
    return Settings(
        test_queue_prefix="test",
        log_format="console",
    )


@pytest.fixture()
async def redis_client(settings: Settings) -> Redis:
    """Client `redis.asyncio` connecté au Redis réel (docker)."""
    client = create_redis(settings)
    yield client
    await client.aclose()


@pytest.fixture()
async def content_queue(settings: Settings):
    """Queue BullMQ `contentQueue` réelle, préfixée `test:` et vidée entre les tests."""
    queue = build_queue(settings.content_queue_name, settings)
    await queue.drain()
    yield queue
    await queue.drain()
    await queue.close()


@pytest.fixture()
async def decision_queue(settings: Settings):
    """Queue BullMQ `decisionQueue` réelle, préfixée `test:` et vidée entre les tests."""
    queue = build_queue(settings.decision_queue_name, settings)
    await queue.drain()
    yield queue
    await queue.drain()
    await queue.close()
