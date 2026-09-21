"""Tests d'intégration du `SpamFilter` (Redis réel) — Tâche 03."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from redis.asyncio import Redis

from app.config.redis import create_redis
from app.config.settings import Settings
from app.errors import TransientFilterError
from app.filters.spam_filter import SpamFilter
from app.schemas.enums import ContentType, FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.result import FilterContext
from tests.fixtures.payloads import make_item

DUP_PREFIX = "mod:spam:dup"
FLOOD_PREFIX = "mod:spam:flood"


def _dup_sha(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


async def _cleanup(redis: Redis, community: str) -> None:
    keys = await redis.keys(f"mod:spam:*:{community}:*")
    if keys:
        await redis.delete(*keys)


def _ctx(community: str) -> FilterContext:
    return FilterContext(
        batch_id="batch-1",
        community_ref=community,
        attempt=0,
        target_classes={RiskClass.SPAM},
    )


@pytest.fixture()
def unique_community() -> str:
    return f"comm-{uuid.uuid4().hex}"


@pytest.mark.integration
async def test_dup_counter_detects_second_duplicate(
    redis_client: Redis, unique_community: str
) -> None:
    flt = SpamFilter(redis_client)
    item_a = make_item(text="free money click here " * 3, user_ref="u-1", content_id="c-1")
    item_b = make_item(text=item_a.text, user_ref="u-1", content_id="c-2")
    ctx = _ctx(unique_community)

    first = await flt.evaluate(item_a, ctx)
    assert first.status == FilterStatus.COMPLETED
    assert first.detections == []

    second = await flt.evaluate(item_b, ctx)
    assert second.status == FilterStatus.COMPLETED
    assert len(second.detections) == 1
    detection = second.detections[0]
    assert detection.risk_class == RiskClass.SPAM
    assert detection.source == Source.BEHAVIOR
    assert detection.score == 0.40
    assert "dup=2" in detection.detail

    await _cleanup(redis_client, unique_community)


@pytest.mark.integration
async def test_flood_above_threshold_ramps_score(redis_client: Redis, unique_community: str) -> None:
    flt = SpamFilter(redis_client, flood_threshold=2)
    ctx = _ctx(unique_community)
    last: object = None
    for index in range(3):
        last = await flt.evaluate(
            make_item(
                text=f"winter snow is falling down the hill of the north side {index}",
                user_ref="spammer",
                content_id=f"c-{index}",
            ),
            ctx,
        )
    assert last is not None
    outcome = last  # type: ignore[assignment]
    assert len(outcome.detections) == 1
    assert outcome.detections[0].score == 0.60  # 3 > 2, <= 4 → 0.60
    assert "flood=3" in outcome.detections[0].detail

    await _cleanup(redis_client, unique_community)


@pytest.mark.integration
async def test_dup_key_has_ttl(redis_client: Redis, unique_community: str) -> None:
    dup_window_sec = 120
    flt = SpamFilter(redis_client, dup_window_sec=dup_window_sec)
    ctx = _ctx(unique_community)
    item = make_item(text="same text content exactly repeated twice", user_ref="u-1")
    await flt.evaluate(item, ctx)

    key = f"{DUP_PREFIX}:{unique_community}:{_dup_sha(item.text)}"
    ttl = await redis_client.ttl(key)
    assert 0 < ttl <= dup_window_sec

    await _cleanup(redis_client, unique_community)


@pytest.mark.integration
async def test_whitespace_text_only_skipped(redis_client: Redis, unique_community: str) -> None:
    flt = SpamFilter(redis_client)
    item = ContentItem.model_construct(
        content_id="c-1",
        content_type=ContentType.COMMENT,
        user_ref="u-1",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        text="   ",
        attachments=[],
    )
    outcome = await flt.evaluate(item, _ctx(unique_community))
    assert outcome.status == FilterStatus.SKIPPED
    assert outcome.detections == []


@pytest.mark.integration
async def test_no_text_no_attachments_skipped(redis_client: Redis, unique_community: str) -> None:
    """Branche défensive §5.1 : ni texte ni attachment → SKIPPED (schéma le refuserait)."""
    flt = SpamFilter(redis_client)
    item = ContentItem.model_construct(
        content_id="c-1",
        content_type=ContentType.COMMENT,
        user_ref="u-1",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        text="",
        attachments=[],
    )
    outcome = await flt.evaluate(item, _ctx(unique_community))
    assert outcome.status == FilterStatus.SKIPPED
    assert outcome.detections == []


@pytest.mark.integration
async def test_text_and_urls_duplicate_detected(redis_client: Redis, unique_community: str) -> None:
    flt = SpamFilter(redis_client)
    ctx = _ctx(unique_community)
    item = make_item(
        text="join our channel for daily prizes and free gifts today everyone",
        user_ref="u-1",
        attachments=[{"type": "image", "url": "https://cdn.example.com/a.png"}],
    )
    item2 = make_item(
        text="join our channel for daily prizes and free gifts today everyone",
        user_ref="u-1",
        attachments=[{"type": "image", "url": "https://cdn.example.com/a.png"}],
    )
    await flt.evaluate(item, ctx)
    outcome = await flt.evaluate(item2, ctx)
    assert len(outcome.detections) == 1
    assert outcome.detections[0].score == 0.40

    await _cleanup(redis_client, unique_community)


@pytest.mark.integration
async def test_unreachable_redis_raises_transient(unique_community: str) -> None:
    down_settings = Settings(redis_port=6399)
    down_client = create_redis(down_settings)
    try:
        flt = SpamFilter(down_client)
        item = make_item(text="hello world this is a longer benign message here today")
        with pytest.raises(TransientFilterError) as excinfo:
            await flt.evaluate(item, _ctx(unique_community))
        assert excinfo.value.filter_name == "SpamFilter"
        assert "c-1" in excinfo.value.content_ids
    finally:
        await down_client.aclose()
