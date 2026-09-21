"""Tests d'intégration du `LinkFilter` — S8 blocklist Redis + fallback Redis KO — Tâche 04."""

from __future__ import annotations

import uuid

import pytest
from redis.asyncio import Redis

from app.config.redis import create_redis
from app.config.settings import Settings
from app.filters.link_filter import LinkFilter
from app.schemas.enums import FilterStatus, RiskClass
from app.schemas.result import FilterContext
from tests.fixtures.payloads import make_item

BLOCKLIST_KEY = "mod:links:blocklist"


def _ctx() -> FilterContext:
    return FilterContext(
        batch_id="batch-1",
        community_ref="community-A",
        attempt=0,
        target_classes={RiskClass.MALICIOUS_LINK, RiskClass.PHISHING},
    )


@pytest.mark.integration
async def test_s8_blocklisted_host_score_one(redis_client: Redis) -> None:
    host = f"blocked-{uuid.uuid4().hex}.com"
    await redis_client.sadd(BLOCKLIST_KEY, host)
    try:
        flt = LinkFilter(redis=redis_client)
        outcome = await flt.evaluate(
            make_item(text=f"check this https://{host}/invite", user_ref="u-1", content_id="c-1"),
            _ctx(),
        )
        assert outcome.status == FilterStatus.COMPLETED
        malicious = [d for d in outcome.detections if d.risk_class == RiskClass.MALICIOUS_LINK]
        assert len(malicious) == 1
        assert malicious[0].score == 1.00  # S8 → 1.00, plafonné
        assert "S8" in malicious[0].detail
    finally:
        await redis_client.srem(BLOCKLIST_KEY, host)


@pytest.mark.integration
async def test_s8_not_in_blocklist_no_score(redis_client: Redis) -> None:
    flt = LinkFilter(redis=redis_client, suspicious_tlds=[])  # tld 'com' non suspicious
    outcome = await flt.evaluate(
        make_item(text="https://example.com/plain ok", user_ref="u-1", content_id="c-1"),
        _ctx(),
    )
    assert outcome.status == FilterStatus.COMPLETED
    assert outcome.detections == []


@pytest.mark.integration
async def test_redis_ko_s8_ignored_no_error() -> None:
    down_client = create_redis(Settings(redis_port=6399))
    try:
        flt = LinkFilter(redis=down_client)
        outcome = await flt.evaluate(
            make_item(text="https://example.com/plain ok", user_ref="u-1", content_id="c-1"),
            _ctx(),
        )
        # Redis KO → S8 ignoré, pas de TransientFilterError, pas de détection
        assert outcome.status == FilterStatus.COMPLETED
        assert outcome.detections == []
    finally:
        await down_client.aclose()
