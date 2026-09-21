"""Tests unitaires du publisher/scheduler — backoff, restriction du payload, erreurs."""

from __future__ import annotations

import pytest

from app.core.publisher import DecisionPublisher, RetryScheduler, restrict_payload
from app.errors import PublishError
from app.schemas.enums import RiskClass
from app.schemas.state import RetryState
from tests.fixtures.payloads import make_item, make_payload


class _StubQueue:
    def __init__(self, *, error: bool = False) -> None:
        self.error = error
        self.add_calls: list[tuple] = []

    async def add(self, name: str, data: dict, opts: dict) -> None:
        if self.error:
            raise ConnectionError("redis down")
        self.add_calls.append((name, data, opts))


@pytest.mark.unit
def test_delay_for_exponential_capped() -> None:
    scheduler = RetryScheduler(_StubQueue(), base_delay_ms=5000, max_delay_ms=300_000)
    assert scheduler.delay_for(0) == 5000
    assert scheduler.delay_for(1) == 10_000
    assert scheduler.delay_for(5) == 160_000
    assert scheduler.delay_for(10) == 300_000  # plafonné


@pytest.mark.unit
def test_restrict_payload_keeps_only_unresolved_with_retry_state() -> None:
    payload = make_payload(
        items=[make_item("c-1"), make_item("c-2")],
        active_classes=[RiskClass.TOXICITY, RiskClass.INSULT],
    )
    retry_state = RetryState(attempt=2, first_job_id="orig", filters={})
    data = restrict_payload(payload, ["c-1"], retry_state)
    assert [item["contentId"] for item in data["items"]] == ["c-1"]
    assert data["retryState"]["attempt"] == 2
    assert data["batchId"] == "batch-1"
    assert set(data["activeClasses"]) == {"TOXICITY", "INSULT"}


@pytest.mark.unit
async def test_schedule_uses_deterministic_job_id_and_restricted_items() -> None:
    queue = _StubQueue()
    scheduler = RetryScheduler(queue, base_delay_ms=5000, max_delay_ms=300_000)  # type: ignore[arg-type]
    payload = make_payload(
        items=[make_item("c-1"), make_item("c-2")],
        active_classes=[RiskClass.TOXICITY, RiskClass.INSULT],
    )
    retry_state = RetryState(attempt=1, first_job_id="orig", filters={})
    await scheduler.schedule(payload, retry_state, ["c-1"])
    name, data, opts = queue.add_calls[0]
    assert name == "moderateBatch"
    assert opts["jobId"] == "batch-1:retry:1"
    assert opts["attempts"] == 1
    assert opts["delay"] == 5000  # delay_for(0) — passage 0 terminé
    assert [item["contentId"] for item in data["items"]] == ["c-1"]


@pytest.mark.unit
async def test_publish_sets_job_id_and_propagates_infra_error() -> None:
    queue = _StubQueue()
    publisher = DecisionPublisher(queue)  # type: ignore[arg-type]
    from app.schemas.decision import DecisionJob

    decision = DecisionJob.model_validate(
        {
            "batchId": "b1",
            "communityRef": "com",
            "content": {"contentId": "c1", "contentType": "comment", "userRef": "u", "timestamp": "2026-01-01T00:00:00Z"},
            "activeClasses": ["TOXICITY"],
            "status": "COMPLETE",
            "detections": [],
            "filtersReport": [],
            "moderatedAt": "2026-01-01T00:00:00Z",
            "processingMs": 5,
        }
    )
    publisher._queue = queue  # type: ignore[attr-defined]
    await publisher.publish(decision)
    name, data, opts = queue.add_calls[0]
    assert name == "decide"
    assert opts["jobId"] == "b1:c1"
    assert opts["attempts"] == 5
    assert data["content"]["contentId"] == "c1"

    failing = _StubQueue(error=True)
    publisher._queue = failing  # type: ignore[attr-defined]
    with pytest.raises(PublishError):
        await publisher.publish(decision)
