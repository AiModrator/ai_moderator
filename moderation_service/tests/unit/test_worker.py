"""Tests unitaires du `Worker` — isolation, mapping état, invariant (§6.2/6.3).

Stubs `DecisionPublisher`/`RetryScheduler` : pas de Redis ici (marqueur `unit`).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.config.settings import Settings
from app.core.pipeline import PipelineBuilder
from app.core.publisher import RetryScheduler, restrict_payload
from app.core.worker import Worker
from app.errors import InvalidJobPayloadError, TransientFilterError
from app.filters.base import BatchFilter, ItemFilter
from app.schemas.decision import DecisionJob
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.result import Detection, FilterOutcome
from tests.fixtures.filters import (
    AlwaysDetectFilter,
    FailOnceThenSucceedFilter,
    PermanentFailFilter,
    SkipFilter,
)
from tests.fixtures.payloads import make_item, make_payload


class StubPublisher:
    """Enregistre les décisions publiées."""

    def __init__(self) -> None:
        self.decisions: list[DecisionJob] = []

    async def publish(self, decision: DecisionJob) -> None:
        self.decisions.append(decision)


class StubScheduler(RetryScheduler):
    """Enregistre les republications retry."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def schedule(self, payload, retry_state, unresolved: list[str]) -> None:
        self.calls.append((payload, retry_state, list(unresolved)))

    def delay_for(self, attempt: int) -> int:
        return 5000 * (2**attempt)


def make_job(payload_dict: dict, job_id: str = "job-id") -> SimpleNamespace:
    return SimpleNamespace(data=payload_dict, id=job_id)


def make_worker(
    registry: list[type],
    *,
    max_retries: int = 3,
    publisher: StubPublisher | None = None,
    scheduler: StubScheduler | None = None,
) -> Worker:
    settings = Settings(
        test_queue_prefix="test",
        log_format="console",
        max_filter_retries=max_retries,
        filters_disabled=[],
    )
    return Worker(
        settings=settings,
        publisher=publisher or StubPublisher(),
        scheduler=scheduler or StubScheduler(),
        builder=PipelineBuilder(registry=registry),
    )


def payload_dict(items: list[ContentItem], active: list[RiskClass]) -> dict:
    return make_payload(items=items, active_classes=active).model_dump(mode="json", by_alias=True)


# ---------------------------------------------------------------------------


class PartialTransientBatchFilter(BatchFilter):
    """Batch : COMPLETED pour `c-1`, `TransientFilterError([c-2])` → PENDING_RETRY pour c-2."""

    NAME = "PartialTransientBatchFilter"
    HANDLED_CLASSES = frozenset({RiskClass.SCAM})
    TIMEOUT_SEC = 2.0

    async def evaluate_batch(self, items: list[ContentItem], ctx) -> list[FilterOutcome]:
        outcomes = [
            FilterOutcome(
                content_id=item.content_id,
                status=FilterStatus.COMPLETED,
                detections=[
                    Detection(risk_class=RiskClass.SCAM, score=0.7, source=Source.TEXT, filter=self.NAME, detail="p")
                ],
            )
            for item in items
            if item.content_id != "c-2"
        ]
        raise TransientFilterError(
            "partial", filter_name=self.NAME, content_ids=["c-2"], partial_outcomes=outcomes
        )


class MissingOutcomeBatchFilter(BatchFilter):
    """Batch qui omet `c-2` sans lever d'erreur → invariant violé → FAILED."""

    NAME = "MissingOutcomeBatchFilter"
    HANDLED_CLASSES = frozenset({RiskClass.SCAM})
    TIMEOUT_SEC = 2.0

    async def evaluate_batch(self, items: list[ContentItem], ctx) -> list[FilterOutcome]:
        return [FilterOutcome(content_id=item.content_id, status=FilterStatus.COMPLETED) for item in items if item.content_id != "c-2"]


class HangingFilter(ItemFilter):
    """ItemFilter lent : `wait_for` timeout → `FilterTimeoutError` → transitoire."""

    NAME = "HangingFilter"
    HANDLED_CLASSES = frozenset({RiskClass.HARASSMENT})
    TIMEOUT_SEC = 0.05

    async def evaluate(self, item: ContentItem, ctx) -> FilterOutcome:
        await asyncio.sleep(0.5)
        return FilterOutcome(content_id=item.content_id, status=FilterStatus.COMPLETED)


@pytest.mark.unit
async def test_complete_pipeline_publishes_compete() -> None:
    worker = make_worker([AlwaysDetectFilter])
    job = make_job(payload_dict([make_item("c-1"), make_item("c-2")], [RiskClass.TOXICITY]))
    result = await worker.process(job)
    assert result.published == ["c-1", "c-2"]
    assert result.retried == []
    assert not result.retry_scheduled
    decision = worker._publisher.decisions[0]
    assert decision.status.value == "COMPLETE"
    assert {d.risk_class.value for d in decision.detections} == {"TOXICITY"}
    report = {r.filter: r for r in decision.filters_report}
    assert report[AlwaysDetectFilter.NAME].status == FilterStatus.COMPLETED
    assert report[AlwaysDetectFilter.NAME].attempts == 1


@pytest.mark.unit
async def test_filter_failure_isolated_other_filters_and_publish_partial() -> None:
    worker = make_worker([AlwaysDetectFilter, PermanentFailFilter])
    job = make_job(payload_dict([make_item("c-1")], [RiskClass.TOXICITY, RiskClass.SEXUAL]))
    result = await worker.process(job)
    assert result.published == ["c-1"]
    assert not result.retry_scheduled
    decision = worker._publisher.decisions[0]
    assert decision.status.value == "PARTIAL"
    report = {r.filter: r for r in decision.filters_report}
    assert report[AlwaysDetectFilter.NAME].status == FilterStatus.COMPLETED
    assert report[PermanentFailFilter.NAME].status == FilterStatus.FAILED
    assert "fixture:permanent_failure" in report[PermanentFailFilter.NAME].error


@pytest.mark.unit
async def test_transient_failure_schedules_selective_retry() -> None:
    FailOnceThenSucceedFilter.reset()
    worker = make_worker([FailOnceThenSucceedFilter])
    job = make_job(payload_dict([make_item("c-1")], [RiskClass.INSULT]))
    result = await worker.process(job)
    assert result.published == []
    assert result.retried == ["c-1"]
    assert result.retry_scheduled
    (payload, retry_state, unresolved) = worker._scheduler.calls[0]
    assert unresolved == ["c-1"]
    assert retry_state.attempt == 1
    items = retry_state.filters[FailOnceThenSucceedFilter.NAME].items
    assert items["c-1"].status == FilterStatus.PENDING_RETRY
    assert items["c-1"].attempts == 1


@pytest.mark.unit
async def test_resolved_items_published_even_while_others_retry() -> None:
    FailOnceThenSucceedFilter.reset()
    worker = make_worker([AlwaysDetectFilter, FailOnceThenSucceedFilter])
    job = make_job(
        payload_dict([make_item("c-1"), make_item("c-2")], [RiskClass.TOXICITY, RiskClass.INSULT])
    )
    result = await worker.process(job)
    assert result.published == ["c-2"]
    assert result.retried == ["c-1"]
    assert result.retry_scheduled
    (payload, retry_state, unresolved) = worker._scheduler.calls[0]
    assert unresolved == ["c-1"]
    restricted = restrict_payload(payload, unresolved, retry_state)
    assert [item["contentId"] for item in restricted["items"]] == ["c-1"]
    always = retry_state.filters[AlwaysDetectFilter.NAME].items
    assert set(always) == {"c-1"}
    assert always["c-1"].status == FilterStatus.COMPLETED
    assert always["c-1"].detections  # détections conservées, jamais ré-exécuté


@pytest.mark.unit
async def test_completed_filters_never_reexecuted_on_retry_pass() -> None:
    """Deuxième passage : AlwaysDetect (COMPLETED) n'est pas ré-exécuté.

    On vérifie via l'état restauré : le compteur d'exécution reste à 1 alors
    que FailOnce est rejoué (sélectif). Le re-processing retombe sur le seul
    filtre en PENDING_RETRY.
    """
    FailOnceThenSucceedFilter.reset()
    worker = make_worker([AlwaysDetectFilter, FailOnceThenSucceedFilter], max_retries=2)
    job = make_job(
        payload_dict([make_item("c-1")], [RiskClass.TOXICITY, RiskClass.INSULT])
    )
    await worker.process(job)
    (payload, retry_state, _unresolved) = worker._scheduler.calls[0]
    assert retry_state.filters[AlwaysDetectFilter.NAME].items["c-1"].attempts == 1

    # Second passage avec le payload de retry — budget déjà consommé → succès.
    retry_worker = make_worker([AlwaysDetectFilter, FailOnceThenSucceedFilter], max_retries=2)
    retry_worker._scheduler = worker._scheduler
    retry_payload = payload.model_copy(update={"retry_state": retry_state})
    job2 = make_job(retry_payload.model_dump(mode="json", by_alias=True), job_id="b:retry:1")
    result = await retry_worker.process(job2)
    assert FailOnceThenSucceedFilter._failure_budget == 0
    assert result.published == ["c-1"]
    assert not result.retry_scheduled
    decision = retry_worker._publisher.decisions[0]
    report = {r.filter: r for r in decision.filters_report}
    assert report[AlwaysDetectFilter.NAME].attempts == 1  # jamais ré-exécuté
    assert report[FailOnceThenSucceedFilter.NAME].attempts == 2
    FailOnceThenSucceedFilter.reset()


@pytest.mark.unit
async def test_retry_exhaustion_publishes_unavailable_partial() -> None:
    FailOnceThenSucceedFilter.reset()
    worker = make_worker([FailOnceThenSucceedFilter], max_retries=0)
    job = make_job(payload_dict([make_item("c-1")], [RiskClass.INSULT]))
    result = await worker.process(job)
    assert result.published == ["c-1"]
    assert not result.retry_scheduled
    assert worker._scheduler.calls == []
    decision = worker._publisher.decisions[0]
    assert decision.status.value == "PARTIAL"
    report = {r.filter: r for r in decision.filters_report}
    assert report[FailOnceThenSucceedFilter.NAME].status == FilterStatus.UNAVAILABLE
    assert report[FailOnceThenSucceedFilter.NAME].attempts == 1


@pytest.mark.unit
async def test_retry_gate_uses_batch_attempt() -> None:
    FailOnceThenSucceedFilter.reset()
    worker = make_worker([FailOnceThenSucceedFilter], max_retries=1)
    job = make_job(payload_dict([make_item("c-1")], [RiskClass.INSULT]))
    await worker.process(job)
    assert worker._scheduler.calls and not worker._publisher.decisions

    (payload, retry_state, _) = worker._scheduler.calls[0]
    assert retry_state.attempt == 1
    FailOnceThenSucceedFilter.reset()
    worker2 = make_worker([FailOnceThenSucceedFilter], max_retries=1)
    worker2._scheduler = worker._scheduler
    retry_payload = payload.model_copy(update={"retry_state": retry_state})
    job2 = make_job(retry_payload.model_dump(mode="json", by_alias=True), job_id="b:retry:1")
    result = await worker2.process(job2)
    # attempt(1) >= max(1) → épuisement immédiat : UNAVAILABLE + publication.
    assert result.published == ["c-1"]
    assert not result.retry_scheduled
    assert len(worker._scheduler.calls) == 1  # pas de seconde republication
    decision = worker2._publisher.decisions[0]
    assert decision.status.value == "PARTIAL"


@pytest.mark.unit
async def test_batch_transient_partial_keeps_successes() -> None:
    worker = make_worker([PartialTransientBatchFilter])
    job = make_job(payload_dict([make_item("c-1"), make_item("c-2")], [RiskClass.SCAM]))
    result = await worker.process(job)
    assert result.published == ["c-1"]
    assert result.retried == ["c-2"]
    (payload, retry_state, _) = worker._scheduler.calls[0]
    items = retry_state.filters[PartialTransientBatchFilter.NAME].items
    assert items["c-2"].status == FilterStatus.PENDING_RETRY
    assert items["c-2"].attempts == 1


@pytest.mark.unit
async def test_batch_missing_outcome_marks_failed() -> None:
    worker = make_worker([MissingOutcomeBatchFilter])
    job = make_job(payload_dict([make_item("c-1"), make_item("c-2")], [RiskClass.SCAM]))
    result = await worker.process(job)
    assert sorted(result.published) == ["c-1", "c-2"]
    assert not result.retry_scheduled
    decisions = {d.content.content_id: d for d in worker._publisher.decisions}
    assert decisions["c-2"].status.value == "PARTIAL"
    report = {r.filter: r for r in decisions["c-2"].filters_report}
    assert report[MissingOutcomeBatchFilter.NAME].status == FilterStatus.FAILED


@pytest.mark.unit
async def test_timeout_is_transient_and_retried() -> None:
    worker = make_worker([HangingFilter])
    job = make_job(payload_dict([make_item("c-1")], [RiskClass.HARASSMENT]))
    result = await worker.process(job)
    assert result.published == []
    assert result.retried == ["c-1"]
    (_payload, retry_state, _) = worker._scheduler.calls[0]
    item = retry_state.filters[HangingFilter.NAME].items["c-1"]
    assert item.status == FilterStatus.PENDING_RETRY
    assert item.attempts == 1
    assert "FilterTimeoutError" in item.last_error


@pytest.mark.unit
async def test_invalid_payload_raises_and_nothing_published() -> None:
    worker = make_worker([AlwaysDetectFilter])
    dup_items = [
        {"contentId": "c-1", "contentType": "comment", "userRef": "u", "timestamp": "2026-01-01T00:00:00Z", "text": "hello"},
        {"contentId": "c-1", "contentType": "comment", "userRef": "u", "timestamp": "2026-01-01T00:00:00Z", "text": "hello"},
    ]
    bad = {
        "batchId": "b",
        "communityRef": "c",
        "activeClasses": ["TOXICITY"],
        "items": dup_items,
    }
    with pytest.raises(InvalidJobPayloadError):
        await worker.process(make_job(bad))
    assert worker._publisher.decisions == []
    assert worker._scheduler.calls == []


@pytest.mark.unit
async def test_never_applicable_filter_skips_and_publishes_compete() -> None:
    worker = make_worker([SkipFilter])
    job = make_job(payload_dict([make_item("c-1", text="promo promo")], [RiskClass.ADVERTISING]))
    result = await worker.process(job)
    assert result.published == ["c-1"]
    decision = worker._publisher.decisions[0]
    assert decision.status.value == "COMPLETE"
    assert decision.detections == []
    report = {r.filter: r for r in decision.filters_report}
    assert report[SkipFilter.NAME].status == FilterStatus.SKIPPED
    assert report[SkipFilter.NAME].attempts == 0
