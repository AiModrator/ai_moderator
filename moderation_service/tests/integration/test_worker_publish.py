"""Publication des items résolus — partielle, épuisement des retries, idempotence du jobId.

Redis réel ; vérifie `jobId = "{batchId}:{contentId}"` et `PARTIAL` sur épuisement (§6.5).
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
from app.schemas.job import ContentBatchJob
from tests.fixtures.payloads import make_item, make_payload
from tests.integration._worker_filters import CountedDetectFilter, RetryOnceFilter

BATCH_ID = "batch-publish"


def make_settings(max_retries: int) -> Settings:
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


async def seed_and_process(content_queue, worker: Worker, payload: ContentBatchJob, job_id: str) -> Job:
    await content_queue.add("moderateBatch", payload.model_dump(mode="json", by_alias=True), {"jobId": job_id, "attempts": 1})
    job = await Job.fromId(content_queue, job_id)
    await worker.process(job)
    return job


@pytest.mark.integration
async def test_resolved_published_while_unresolved_retried(content_queue, decision_queue) -> None:
    CountedDetectFilter.reset()
    RetryOnceFilter.reset(budget=1)  # c-1 transitoire, c-2 succès
    settings = make_settings(max_retries=3)
    worker = make_worker(content_queue, decision_queue, settings)
    payload = make_payload(
        batch_id=BATCH_ID,
        items=[make_item("c-1"), make_item("c-2")],
        active_classes=[RiskClass.TOXICITY, RiskClass.INSULT],
    )
    await seed_and_process(content_queue, worker, payload, "batch-publish-init")

    decision_c1 = await Job.fromId(decision_queue, f"{BATCH_ID}:c-1")
    decision_c2 = await Job.fromId(decision_queue, f"{BATCH_ID}:c-2")
    assert decision_c1 is None          # en attente de retry
    assert decision_c2 is not None      # résolu dès le 1er passage → publié
    parsed = DecisionJob.model_validate(decision_c2.data)
    assert parsed.status.value == "COMPLETE"

    retry_job = await Job.fromId(content_queue, f"{BATCH_ID}:retry:1")
    assert retry_job is not None
    assert [item["contentId"] for item in retry_job.data["items"]] == ["c-1"]


@pytest.mark.integration
async def test_retry_exhaustion_publishes_partial(content_queue, decision_queue) -> None:
    CountedDetectFilter.reset()
    RetryOnceFilter.reset(budget=1)
    settings = make_settings(max_retries=0)
    worker = make_worker(content_queue, decision_queue, settings)
    payload = make_payload(
        batch_id=BATCH_ID,
        items=[make_item("c-1")],
        active_classes=[RiskClass.INSULT, RiskClass.TOXICITY],
    )
    await seed_and_process(content_queue, worker, payload, "batch-exhaust-init")

    decision = await Job.fromId(decision_queue, f"{BATCH_ID}:c-1")
    assert decision is not None
    parsed = DecisionJob.model_validate(decision.data)
    assert parsed.status.value == "PARTIAL"
    report = {r.filter: r for r in parsed.filters_report}
    assert report[RetryOnceFilter.NAME].status == FilterStatus.UNAVAILABLE
    assert report[RetryOnceFilter.NAME].attempts == 1
    assert report[CountedDetectFilter.NAME].status == FilterStatus.COMPLETED

    retry = await Job.fromId(content_queue, f"{BATCH_ID}:retry:1")
    assert retry is None  # plus de retry après épuisement


@pytest.mark.integration
async def test_decision_job_id_is_idempotent(decision_queue) -> None:
    from datetime import UTC, datetime

    from app.schemas.decision import (
        AggregatedDetection,
        ContentRef,
        DecisionJob,
        DecisionStatus,
        FilterReport,
    )
    from app.schemas.enums import ContentType, Source
    from app.schemas.result import Detection

    decision = DecisionJob(
        batch_id=BATCH_ID,
        community_ref="community-A",
        content=ContentRef(
            content_id="post-test",
            content_type=ContentType.COMMENT,
            user_ref="u-1",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        active_classes=[RiskClass.TOXICITY],
        status=DecisionStatus.COMPLETE,
        detections=[
            AggregatedDetection(
                risk_class=RiskClass.TOXICITY,
                score=0.9,
                sources=[Source.TEXT],
                evidence=[
                    Detection(risk_class=RiskClass.TOXICITY, score=0.9, source=Source.TEXT, filter=CountedDetectFilter.NAME)
                ],
            )
        ],
        filters_report=[FilterReport(filter=CountedDetectFilter.NAME, status=FilterStatus.COMPLETED, attempts=1)],
        moderated_at=datetime(2026, 1, 1, tzinfo=UTC),
        processing_ms=0,
    )
    publisher = DecisionPublisher(decision_queue)
    await publisher.publish(decision)
    await publisher.publish(decision)  # même jobId → même job

    job = await Job.fromId(decision_queue, f"{BATCH_ID}:post-test")
    assert job is not None
    assert job.id == f"{BATCH_ID}:post-test"
    assert await decision_queue.getJobCountByTypes("waiting") == 1
