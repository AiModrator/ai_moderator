"""Payload `contentQueue` invalide → `InvalidJobPayloadError`, rien n'est publié ni retryé.

Redis réel (queues préfixées `test:`) ; le job est marqué `failed` par BullMQ
quand le handler du Worker lève (simulé ici par un appel direct à `process`).
"""

from __future__ import annotations

import pytest

from app.config.settings import Settings
from app.core.filter_factory import FilterFactory
from app.core.pipeline import PipelineBuilder
from app.core.publisher import DecisionPublisher, RetryScheduler
from app.core.worker import Worker
from app.errors import InvalidJobPayloadError
from tests.integration._worker_filters import CountedDetectFilter


def _fake_job(data):
    from types import SimpleNamespace

    return SimpleNamespace(data=data, id="job-id")


@pytest.mark.integration
async def test_invalid_payload_is_rejected(content_queue, decision_queue) -> None:
    settings = Settings(test_queue_prefix="test", log_format="console", max_filter_retries=3)
    worker = Worker(
        settings=settings,
        publisher=DecisionPublisher(decision_queue),
        scheduler=RetryScheduler(content_queue, base_delay_ms=0, max_delay_ms=0),
        builder=PipelineBuilder(registry=[CountedDetectFilter]),
        factory=FilterFactory(settings),
    )
    # `activeClasses` vide → rien à faire : payload invalide (§3.2).
    bad_payload = {
        "batchId": "batch-invalid",
        "communityRef": "community-A",
        "activeClasses": [],
        "items": [
            {"contentId": "c-1", "contentType": "comment", "userRef": "u-1", "timestamp": "2026-01-01T00:00:00Z", "text": "hello"}
        ],
    }
    with pytest.raises(InvalidJobPayloadError):
        await worker.process(_fake_job(bad_payload))

    assert await decision_queue.getJobCountByTypes("waiting") == 0
    assert await decision_queue.getJobCountByTypes("delayed") == 0
    assert await content_queue.getJobCountByTypes("waiting") == 0


@pytest.mark.integration
async def test_invalid_text_and_attachments_rejected(content_queue, decision_queue) -> None:
    settings = Settings(test_queue_prefix="test", log_format="console", max_filter_retries=3)
    worker = Worker(
        settings=settings,
        publisher=DecisionPublisher(decision_queue),
        scheduler=RetryScheduler(content_queue, base_delay_ms=0, max_delay_ms=0),
        builder=PipelineBuilder(registry=[CountedDetectFilter]),
        factory=FilterFactory(settings),
    )
    bad_payload = {
        "batchId": "batch-invalid-2",
        "communityRef": "community-A",
        "activeClasses": ["TOXICITY"],
        "items": [
            {"contentId": "c-1", "contentType": "comment", "userRef": "u-1", "timestamp": "2026-01-01T00:00:00Z", "text": None, "attachments": []}
        ],
    }
    with pytest.raises(InvalidJobPayloadError):
        await worker.process(_fake_job(bad_payload))

    assert await decision_queue.getJobCountByTypes("waiting") == 0


def _fake_job(data):
    from types import SimpleNamespace

    return SimpleNamespace(data=data, id="job-id")
