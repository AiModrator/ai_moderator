"""Cycle complet du retry sélectif : republication → re-traitement → complétion.

Redis réel (queues BullMQ préfixées `test:`), filtres de test réels
(compteurs d'appels) — main.md §6.1–6.5.
"""

from __future__ import annotations

import pytest
from bullmq import Job

from app.config.settings import Settings
from app.core.filter_factory import FilterFactory
from app.core.pipeline import PipelineBuilder
from app.core.publisher import DecisionPublisher, RetryScheduler
from app.core.worker import Worker
from app.schemas.decision import DecisionJob
from app.schemas.enums import FilterStatus, RiskClass
from tests.fixtures.payloads import make_item, make_payload
from tests.integration._worker_filters import CountedDetectFilter, RetryOnceFilter

BATCH_ID = "batch-retry"


def make_settings(max_retries: int = 3) -> Settings:
    return Settings(
        test_queue_prefix="test",
        log_format="console",
        max_filter_retries=max_retries,
        retry_base_delay_ms=0,
        retry_max_delay_ms=0,
    )


def make_worker(content_queue, decision_queue, settings: Settings) -> Worker:
    return Worker(
        settings=settings,
        publisher=DecisionPublisher(decision_queue),
        scheduler=RetryScheduler(content_queue, base_delay_ms=0, max_delay_ms=0),
        builder=PipelineBuilder(registry=[CountedDetectFilter, RetryOnceFilter]),
        factory=FilterFactory(settings),
    )


async def fetch_decision(decision_queue, content_id: str) -> DecisionJob | None:
    job = await Job.fromId(decision_queue, f"{BATCH_ID}:{content_id}")
    if job is None:
        return None
    return DecisionJob.model_validate(job.data)


@pytest.mark.integration
async def test_selective_retry_completes_and_never_reexecutes_completed(content_queue, decision_queue) -> None:
    CountedDetectFilter.reset()
    RetryOnceFilter.reset(budget=1)
    settings = make_settings(max_retries=3)
    worker = make_worker(content_queue, decision_queue, settings)

    payload = make_payload(
        batch_id=BATCH_ID,
        items=[make_item("c-1")],
        active_classes=[RiskClass.TOXICITY, RiskClass.INSULT],
    )
    await content_queue.add("moderateBatch", payload.model_dump(mode="json", by_alias=True), {"jobId": "batch-retry-init", "attempts": 1})
    job = await Job.fromId(content_queue, "batch-retry-init")

    # ---- 1er passage : CountedDetect COMPLETED, RetryOnce transitoire → PERSONNE publié, retry planifié
    result = await worker.process(job)
    assert result.published == []
    assert result.retried == ["c-1"]
    assert CountedDetectFilter.calls() == 1
    assert RetryOnceFilter.calls() == 1
    assert await fetch_decision(decision_queue, "c-1") is None

    retry_job = await Job.fromId(content_queue, f"{BATCH_ID}:retry:1")
    assert retry_job is not None
    assert [item["contentId"] for item in retry_job.data["items"]] == ["c-1"]
    assert retry_job.data["retryState"]["attempt"] == 1

    # ---- 2e passage : seul RetryOnce (PENDING_RETRY) est rejoué ; CountedDetect conservé
    worker2 = make_worker(content_queue, decision_queue, settings)
    result2 = await worker2.process(retry_job)
    assert result2.published == ["c-1"]
    assert not result2.retry_scheduled
    assert CountedDetectFilter.calls() == 1  # jamais ré-exécuté
    assert RetryOnceFilter.calls() == 2

    decision = await fetch_decision(decision_queue, "c-1")
    assert decision is not None
    assert decision.status.value == "COMPLETE"
    assert {d.risk_class.value for d in decision.detections} == {"TOXICITY", "INSULT"}
    report = {r.filter: r for r in decision.filters_report}
    assert report[CountedDetectFilter.NAME].attempts == 1
    assert report[RetryOnceFilter.NAME].attempts == 2
    assert report[RetryOnceFilter.NAME].status == FilterStatus.COMPLETED
