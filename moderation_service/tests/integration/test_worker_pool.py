"""`WorkerPool` (§9.2) — concurrence bornée, scale simulé, drain à l'arrêt.

Redis réel (queues dédiées `poolContentQueue`/`poolDecisionQueue` sous le préfixe
`test:` pour des compteurs isolés). `SlowFilter` mesure la concurrence réelle
(`peak_active`) : jamais plus que `semaphore.capacity` jobs simultanés.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.config.settings import Settings
from app.core.filter_factory import FilterFactory
from app.core.pipeline import PipelineBuilder
from app.core.publisher import DecisionPublisher, RetryScheduler, build_queue
from app.core.resource_monitor import ResourceMonitor
from app.core.worker import Worker
from app.core.worker_pool import DynamicSemaphore, WorkerPool
from app.schemas.enums import RiskClass
from tests.fixtures.filters import SlowFilter
from tests.fixtures.payloads import make_item, make_payload

CONTENT_Q = "poolContentQueue"
DECISION_Q = "poolDecisionQueue"


def pool_settings(**overrides) -> Settings:
    base = dict(
        test_queue_prefix="test",
        log_format="console",
        worker_pool_min=2,
        worker_pool_initial=3,
        worker_pool_max=4,
        scale_step=2,
        scale_cooldown_sec=0,
        monitor_interval_sec=0.1,
        max_filter_retries=2,
    )
    base.update(overrides)
    return Settings(**base)


class FakeMetrics:
    """Métriques réglables pour simuler CPU/RAM côté `ResourceMonitor`."""

    def __init__(self, cpu: float = 70.0, ram: float = 75.0) -> None:
        # valeurs par défaut : zone neutre → aucun auto-scale parasite
        self.cpu = cpu
        self.ram = ram

    def cpu_percent(self) -> float:
        return self.cpu

    def ram_percent(self) -> float:
        return self.ram


PROCESSED: list[str] = []


async def _start_pool(settings: Settings):
    content = build_queue(CONTENT_Q, settings)
    decision = build_queue(DECISION_Q, settings)
    await content.drain()
    await decision.drain()
    sem = DynamicSemaphore(settings.worker_pool_initial, max_capacity=settings.worker_pool_max)
    metrics = FakeMetrics()
    monitor = ResourceMonitor(settings, sem, metrics=metrics)

    def make_worker() -> Worker:
        from app.core.worker import Worker as _W

        worker = _W(
            settings=settings,
            publisher=DecisionPublisher(decision),
            scheduler=RetryScheduler(content, base_delay_ms=0, max_delay_ms=0),
            builder=PipelineBuilder(registry=[SlowFilter]),
            factory=FilterFactory(settings),
        )
        original_process = worker.process

        async def wrapped(job) -> object:
            PROCESSED.append(job.id)
            return await original_process(job)

        worker.process = wrapped  # type: ignore[method-assign]
        return worker

    pool = WorkerPool(settings, make_worker=make_worker, semaphore=sem, monitor=monitor, queue_name=CONTENT_Q)
    pool_task = asyncio.create_task(pool.start())
    return content, decision, pool, metrics, pool_task


async def seed(content, count: int, batch_prefix: str) -> list[str]:
    """Ajoute `count` jobs avec des jobId uniques ; retourne ces jobId.

    Les jobId fixes seraient des no-op au second run : BullMQ dédoublonne par
    `jobId` et `drain()` ne purge pas les jobs `completed`.
    """
    job_ids: list[str] = []
    for _i in range(count):
        job_id = f"{batch_prefix}-{uuid.uuid4().hex[:8]}"
        payload = make_payload(
            batch_id=job_id,
            items=[make_item(f"pool-{job_id}")],
            active_classes=[RiskClass.VIOLENCE],
        )
        await content.add(
            "moderateBatch",
            payload.model_dump(mode="json", by_alias=True),
            {"jobId": job_id},
        )
        job_ids.append(job_id)
    return job_ids


async def wait_until(predicate, timeout: float = 5.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("condition non atteinte dans le délai")


async def wait_count(queue, state: str, expected: int, timeout: float = 8.0) -> None:
    """Attend qu'une queue atteigne un nombre cible de jobs dans un état."""
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        n = await queue.getJobCountByTypes(state)
        if n >= expected:
            return
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError(f"{state}={n} != {expected} dans le délai")
        await asyncio.sleep(0.05)


@pytest.mark.integration
async def test_concurrency_bounded_by_capacity() -> None:
    PROCESSED.clear()
    SlowFilter.reset()
    settings = pool_settings(worker_pool_initial=3, worker_pool_max=4)
    content, decision, pool, _, pool_task = await _start_pool(settings)
    try:
        job_ids = await seed(content, 6, "bnd")
        await wait_until(lambda: SlowFilter.peak_active() >= 3)
        await asyncio.sleep(0.2)
        assert SlowFilter.peak_active() <= 3  # au plus capacity jobs simultanés
        assert pool.stats()["capacity"] == 3
        # drain : les 6 lots ont tous produit une décision, rien n'est perdu
        await wait_count(decision, "waiting", 6)
        assert await content.getJobCountByTypes("waiting") == 0
        assert await decision.getJobCountByTypes("delayed") == 0
        # le garde-fou anti-relivraison (bullmq « at least once ») : chaque
        # jobId n'est traité qu'une seule fois
        assert sorted(PROCESSED) == sorted(job_ids)
        await pool.stop()
    finally:
        await pool.stop()
        await asyncio.wait_for(pool_task, timeout=10)
        await content.close()
        await decision.close()


@pytest.mark.integration
async def test_scale_simulation_and_graceful_stop() -> None:
    PROCESSED.clear()
    SlowFilter.reset()
    settings = pool_settings(worker_pool_initial=3, worker_pool_max=4)
    content, decision, pool, metrics, pool_task = await _start_pool(settings)
    try:
        job_ids = await seed(content, 4, "sca")
        await wait_until(lambda: SlowFilter.peak_active() >= 3)
        stats = pool.stats()
        assert stats["capacity"] == 3 and stats["scale_events"] == 0

        metrics.cpu = 99
        metrics.ram = 99  # RAM critique → backpressure
        await wait_until(lambda: pool.stats()["capacity"] == 0)
        assert pool.stats()["scale_events"] == 1

        metrics.cpu = 70
        metrics.ram = 75  # retour zone neutre → WORKER_POOL_MIN (hors backpressure)
        await wait_until(lambda: pool.stats()["capacity"] == 2)
        assert pool.stats()["scale_events"] == 2

        # zone neutre + waiting == 0 → pas de scale up
        await asyncio.sleep(0.3)
        assert pool.stats()["capacity"] == 2

        await wait_count(decision, "waiting", 4)  # aucun job perdu au drain
        assert sorted(PROCESSED) == sorted(job_ids)
        await pool.stop()
    finally:
        await pool.stop()
        await asyncio.wait_for(pool_task, timeout=10)
        await content.close()
        await decision.close()


@pytest.mark.integration
async def test_invalid_job_fails_without_losing_others() -> None:
    PROCESSED.clear()
    SlowFilter.reset()
    settings = pool_settings(worker_pool_initial=2, worker_pool_max=4)
    content, decision, pool, _, pool_task = await _start_pool(settings)
    try:
        bad_payload = {
            "batchId": "pool-invalid",
            "communityRef": "community-A",
            "activeClasses": [],
            "items": [
                {"contentId": "bad", "contentType": "comment", "userRef": "u", "timestamp": "2026-01-01T00:00:00Z", "text": "x"}
            ],
        }
        bad_job_id = f"pool-invalid-{uuid.uuid4().hex[:8]}"
        await content.add("moderateBatch", bad_payload, {"jobId": bad_job_id})
        job_ids = await seed(content, 2, "ok")
        await wait_until(lambda: len(PROCESSED) >= 3)
        # le job invalide échoue (BullMQ : handler lève InvalidJobPayloadError → failed),
        # les autres produisent bien une décision (2 survivors)
        await wait_count(decision, "waiting", 2)
        assert sorted(PROCESSED) == sorted(job_ids + [bad_job_id])
        assert await content.getJobCountByTypes("failed") >= 1
        await pool.stop()
    finally:
        await pool.stop()
        await asyncio.wait_for(pool_task, timeout=10)
        await content.close()
        await decision.close()
