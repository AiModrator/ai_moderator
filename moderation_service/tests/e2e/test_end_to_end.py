"""Parcours de bout en bout (main.md §12) : `contentQueue` → `WorkerPool` → `decisionQueue`.

Redis réel (queues préfixées `test:` et vidées), AI Gateway simulée avec `respx`.
Le scénario inclut un item en erreur transitoire (résultat manquant pour `c-2`
au 1er passage) résolu au retry, sans ré-exécuter `SpamFilter` ni `c-1`.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import suppress

import httpx
import pytest
import respx
from bullmq import Job

from app.clients.ai_gateway import AIGatewayClient
from app.config.redis import create_redis
from app.config.settings import Settings
from app.core.publisher import build_queue
from app.filters.image_ai_filter import ImageAIFilter
from app.filters.lexicon_filter import LexiconFilter
from app.filters.lexicon_repository import LexiconRepository
from app.filters.link_filter import LinkFilter
from app.filters.spam_filter import SpamFilter
from app.filters.text_ai_filter import TextAIFilter
from app.schemas.decision import DecisionJob
from app.schemas.enums import FilterStatus, RiskClass, Source
from main import build_pool
from tests.fixtures.payloads import make_item, make_payload

GATEWAY = "http://gateway"

# Registre de production explicite : le registre global peut être pollué par les
# filtres de test (AlwaysDetectFilter, …) quand toute la suite tourne dans le même
# processus pytest.
PRODUCTION_FILTERS = [SpamFilter, LinkFilter, LexiconFilter, TextAIFilter, ImageAIFilter]


def e2e_settings() -> Settings:
    return Settings(
        test_queue_prefix="test",
        log_format="console",
        worker_pool_min=2,
        worker_pool_initial=4,
        worker_pool_max=4,
        monitor_interval_sec=3600,  # pas de tick d'auto-scaling pendant le test
        max_filter_retries=3,
        retry_base_delay_ms=0,
        retry_max_delay_ms=0,
        ai_gateway_url=GATEWAY,
        ai_text_min_chars=2,
    )


async def _wait_for_decisions(decision_queue, count: int, timeout: float = 15.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        waiting = await decision_queue.getJobCountByTypes("waiting")
        if waiting >= count:
            return
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError(f"decisionQueue n'a pas atteint {count} jobs en attente ({waiting})")
        await asyncio.sleep(0.05)


@pytest.mark.e2e
@respx.mock
async def test_end_to_end_batch_two_items_with_transient_retry() -> None:
    settings = e2e_settings()
    run = uuid.uuid4().hex[:8]
    batch_id = f"e2e-{run}"
    community_ref = f"community-{run}"

    redis_client = create_redis(settings)
    lexicon = LexiconRepository()
    lexicon.load()
    gateway = AIGatewayClient(
        GATEWAY,
        timeout_sec=settings.ai_request_timeout_sec,
        max_parallel=settings.ai_max_parallel_requests,
    )

    calls: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        item_ids = [item["id"] for item in json.loads(request.content)["items"]]
        calls.append(item_ids)
        if len(calls) == 1:
            # 1er passage : seul c-1 est renvoyé → c-2 manquant = transitoire.
            results = [{"id": "c-1", "score": 0.7, "reason": "toxic"}]
        else:
            # retry : c-2 est résolu.
            results = [{"id": "c-2", "score": 0.6, "reason": "toxic"}]
        return httpx.Response(200, json={"model": "e2e-model", "results": results})

    respx.post(f"{GATEWAY}/v1/moderation/TOXICITY").mock(side_effect=handler)

    content = build_queue(settings.content_queue_name, settings)
    decision = build_queue(settings.decision_queue_name, settings)
    await content.drain()
    await decision.drain()

    pool = build_pool(
        settings,
        redis_client=redis_client,
        gateway=gateway,
        lexicon=lexicon,
        registry=PRODUCTION_FILTERS,
    )
    pool_task = asyncio.create_task(pool.start(install_signals=False))
    try:
        payload = make_payload(
            batch_id=batch_id,
            community_ref=community_ref,
            items=[
                make_item("c-1", text="I will hurt you", user_ref=f"u-{run}-1"),
                make_item("c-2", text="you are worthless", user_ref=f"u-{run}-2"),
            ],
            active_classes=[RiskClass.SPAM, RiskClass.TOXICITY],
        )
        await content.add(
            "moderateBatch",
            payload.model_dump(mode="json", by_alias=True),
            {"jobId": batch_id, "attempts": 1},
        )

        await _wait_for_decisions(decision, 2)

        d1 = await Job.fromId(decision, f"{batch_id}:c-1")
        d2 = await Job.fromId(decision, f"{batch_id}:c-2")
        assert d1 is not None and d2 is not None
        decision1 = DecisionJob.model_validate(d1.data)
        decision2 = DecisionJob.model_validate(d2.data)

        # Deux jobs au jobId déterministe, statut COMPLETE, détection TOXICITY agrégée.
        assert decision1.status.value == "COMPLETE"
        assert decision2.status.value == "COMPLETE"
        assert {d.risk_class.value for d in decision1.detections} == {"TOXICITY"}
        assert {d.risk_class.value for d in decision2.detections} == {"TOXICITY"}

        toxicity1 = next(d for d in decision1.detections if d.risk_class == RiskClass.TOXICITY)
        toxicity2 = next(d for d in decision2.detections if d.risk_class == RiskClass.TOXICITY)
        assert toxicity1.score == pytest.approx(0.7)
        assert toxicity2.score == pytest.approx(0.6)
        assert toxicity1.sources == [Source.TEXT]
        assert toxicity1.evidence[0].filter == "TextAIFilter"

        # filtersReport complet : SpamFilter + TextAIFilter, retry tracé sur c-2.
        report1 = {r.filter: r for r in decision1.filters_report}
        report2 = {r.filter: r for r in decision2.filters_report}
        assert set(report1) == {"SpamFilter", "TextAIFilter"}
        assert report1["SpamFilter"].status == FilterStatus.COMPLETED
        assert report1["TextAIFilter"].attempts == 1
        assert report2["TextAIFilter"].attempts == 2  # c-2 a été résolu au retry

        # Le fan-out a appelé la gateway exactement 2 fois (1er passage + retry).
        assert calls == [["c-1", "c-2"], ["c-2"]]
    finally:
        await pool.stop()
        pool_task.cancel()
        with suppress(asyncio.CancelledError):
            await pool_task
        await gateway.aclose()
        await content.close()
        await decision.close()
        await redis_client.aclose()
