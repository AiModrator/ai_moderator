"""`Worker` — orchestration d'un lot : isolation (filtre × item), retry sélectif, publication (§6)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

import structlog
from pydantic import ValidationError

from app.config.settings import Settings
from app.core.aggregator import ResultAggregator
from app.core.filter_factory import FilterFactory
from app.core.pipeline import PipelineBuilder
from app.core.publisher import DecisionPublisher, RetryScheduler
from app.errors import (
    FilterTimeoutError,
    InvalidJobPayloadError,
    ItemFilterError,
    PermanentFilterError,
    TransientFilterError,
)
from app.filters.base import BaseFilter, BatchFilter, ItemFilter
from app.schemas.enums import FilterStatus
from app.schemas.job import ContentBatchJob, ContentItem
from app.schemas.result import FilterContext, FilterOutcome
from app.schemas.state import BatchState

_RETRY_PENDING = frozenset({FilterStatus.PENDING, FilterStatus.PENDING_RETRY})


@dataclass
class ProcessResult:
    """Bilan d'un passage : items publiés / en attente de retry."""

    batch_id: str
    items: int = 0
    published: list[str] = field(default_factory=list)
    retried: list[str] = field(default_factory=list)
    retry_scheduled: bool = False
    duration_ms: int = 0


class Worker:
    """Exécute les étapes §6.1 pour un job `contentQueue`.

    Aucune exception de filtre n'en sort : `run_item_filter`/`run_batch_filter`
    tracent l'état dans `BatchState`. Seules `InvalidJobPayloadError` (payload
    invalide) et `PublishError` (infra Redis/BullMQ) remontent à BullMQ.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        publisher: DecisionPublisher,
        scheduler: RetryScheduler,
        builder: PipelineBuilder | None = None,
        factory: FilterFactory | None = None,
        aggregator: ResultAggregator | None = None,
    ) -> None:
        self._settings = settings
        self._publisher = publisher
        self._scheduler = scheduler
        self._builder = builder or PipelineBuilder()
        self._factory = factory or FilterFactory(settings)
        self._aggregator = aggregator or ResultAggregator()
        self._logger = structlog.get_logger()
        self._state: BatchState | None = None
        self._items_by_id: dict[str, ContentItem] = {}

    # ------------------------------------------------------------------ §6.1

    async def process(self, job: Any) -> ProcessResult:
        """Étapes §6.1 : validation → état → pipeline → gather → publication → retry."""
        t0 = monotonic()
        job_id = getattr(job, "id", "") or ""
        try:
            payload = ContentBatchJob.model_validate(job.data)
        except ValidationError as exc:
            self._logger.error("job.invalid", jobId=job_id, error=str(exc))
            raise InvalidJobPayloadError(str(exc)) from exc

        logger = self._logger.bind(
            jobId=job_id, batchId=payload.batch_id, communityRef=payload.community_ref
        )
        self._items_by_id = {item.content_id: item for item in payload.items}

        state = BatchState.from_retry(payload, payload.retry_state, self._settings.max_filter_retries)
        self._state = state

        pipeline, targets = self._builder.build(
            payload.active_classes, disabled=set(self._settings.filters_disabled)
        )
        contexts = PipelineBuilder.build_contexts(
            payload.batch_id, payload.community_ref, state.attempt, targets
        )

        for cls in pipeline:
            state.ensure_filter(cls.NAME, [item.content_id for item in payload.items])

        tasks = self._plan_tasks(pipeline, contexts, payload.items)
        await asyncio.gather(*tasks)

        result = ProcessResult(batch_id=payload.batch_id, items=len(payload.items))
        if not pipeline:
            for item in payload.items:
                await self._publish_item(item, pipeline, state, logger, result)
        else:
            await self._finish_pass(payload, pipeline, state, logger, result)

        result.duration_ms = int((monotonic() - t0) * 1000)
        logger.info(
            "job.done",
            items=result.items,
            published=len(result.published),
            retried=len(result.retried),
            retryScheduled=result.retry_scheduled,
            durationMs=result.duration_ms,
        )
        return result

    # ------------------------------------------------------------ plan / fin

    def _plan_tasks(self, pipeline: list[type[BaseFilter]], contexts: dict[str, FilterContext], items: list[ContentItem]) -> list[asyncio.Task]:
        """Construit les tâches d'exécution (§6.1 étape 5) ; non-applicables → SKIPPED."""
        tasks: list[asyncio.Task] = []
        for cls in pipeline:
            name = cls.NAME
            ctx = contexts[name]
            instance = self._factory.build(cls)
            pending = [item for item in items if self._state_is(name, item.content_id) in _RETRY_PENDING]
            applicable: list[ContentItem] = []
            for item in pending:
                if instance.is_applicable(item):
                    applicable.append(item)
                else:
                    self._state.mark_skipped(name, item.content_id)
            if not applicable:
                continue
            if issubclass(cls, BatchFilter):
                tasks.append(asyncio.create_task(self.run_batch_filter(instance, applicable, ctx)))
            else:
                for item in applicable:
                    tasks.append(asyncio.create_task(self.run_item_filter(instance, item, ctx)))
        return tasks

    async def _finish_pass(
        self,
        payload: ContentBatchJob,
        pipeline: list[type[BaseFilter]],
        state: BatchState,
        logger,
        result: ProcessResult,
    ) -> None:
        resolved = set(state.resolved_items())
        unresolved = [item.content_id for item in payload.items if item.content_id not in resolved]

        if unresolved and state.attempt < self._settings.max_filter_retries:
            # §6.1 étape 9 : republication du bajo restrict + retryState.
            next_attempt = state.attempt + 1
            retry_state = state.to_retry_state(unresolved, next_attempt)
            delay = self._scheduler.delay_for(next_attempt - 1)
            await self._scheduler.schedule(payload, retry_state, unresolved)
            result.retried = unresolved
            result.retry_scheduled = True
            logger.info(
                "batch.retry_scheduled",
                count=len(unresolved),
                delayMs=delay,
                nextAttempt=next_attempt,
            )

        # Étape 8 : items résolus → publication (avant OU après le retry, indépendant).
        for content_id in sorted(resolved):
            await self._publish_item(self._items_by_id[content_id], pipeline, state, logger, result)

        if unresolved and state.attempt >= self._settings.max_filter_retries:
            # Épuisement : PENDING_RETRY → UNAVAILABLE, puis publication (PARTIAL).
            logger.warning("batch.retry_exhausted", attempt=state.attempt, count=len(unresolved))
            for content_id in unresolved:
                self._exhaust_content(state, content_id)
                await self._publish_item(self._items_by_id[content_id], pipeline, state, logger, result)

    async def _publish_item(self, item: ContentItem, pipeline, state: BatchState, logger, result: ProcessResult) -> None:
        decision = self._aggregator.aggregate(item, state, pipeline, processing_ms=result.duration_ms)
        await self._publisher.publish(decision)
        logger.info("decision.published", contentId=item.content_id, status=decision.status.value)
        result.published.append(item.content_id)

    @staticmethod
    def _exhaust_content(state: BatchState, content_id: str) -> None:
        for fstate in state.filters.values():
            istate = fstate.items.get(content_id)
            if istate is not None and istate.status == FilterStatus.PENDING_RETRY:
                istate.status = FilterStatus.UNAVAILABLE

    # ------------------------------------------------------- §6.2 / §6.3 run

    async def run_item_filter(self, F: ItemFilter, item: ContentItem, ctx: FilterContext) -> None:
        """Isolation élémentaire : mapping exception → état (§6.2)."""
        name = F.NAME
        try:
            outcome = await asyncio.wait_for(F.evaluate(item, ctx), timeout=F.TIMEOUT_SEC)
            self._state.set(name, outcome)
        except TimeoutError as exc:
            self._state.mark_transient(name, item.content_id, FilterTimeoutError(str(exc), filter_name=name))
        except TransientFilterError as exc:
            self._state.mark_transient(name, item.content_id, exc)
        except (ItemFilterError, PermanentFilterError) as exc:
            self._state.mark_failed(name, item.content_id, exc)
        except Exception as exc:  # bug de filtre → FAILED ; ne remonte jamais
            self._logger.error("filter.unexpected_error", filter=name, contentId=item.content_id, error=str(exc))
            self._state.mark_failed(name, item.content_id, exc)

    async def run_batch_filter(self, F: BatchFilter, items: list[ContentItem], ctx: FilterContext) -> None:
        """Isolation par lot : outcomes partiels conservés, sous-ensemble listé (§6.3)."""
        name = F.NAME
        try:
            outcomes = await asyncio.wait_for(F.evaluate_batch(items, ctx), timeout=F.TIMEOUT_SEC)
            self._apply_outcomes_invariant(name, items, outcomes)
        except TimeoutError as exc:
            for item in items:
                self._state.mark_transient(name, item.content_id, FilterTimeoutError(str(exc), filter_name=name))
        except TransientFilterError as exc:
            self._state.set_many(name, exc.partial_outcomes)
            for content_id in exc.content_ids or [item.content_id for item in items]:
                self._state.mark_transient(name, content_id, exc)
        except PermanentFilterError as exc:
            self._state.set_many(name, exc.partial_outcomes)
            for content_id in exc.content_ids or [item.content_id for item in items]:
                self._state.mark_failed(name, content_id, exc)
        except Exception as exc:  # bug de filtre → FAILED pour tout le lot ; ne remonte jamais
            self._logger.error("filter.unexpected_error", filter=name, itemCount=len(items), error=str(exc))
            for item in items:
                self._state.mark_failed(name, item.content_id, exc)

    def _apply_outcomes_invariant(self, name: str, items: list[ContentItem], outcomes: list[FilterOutcome]) -> None:
        """Invariant §4.1 : exactement UN outcome par item, sinon FAILED pour les manquants."""
        by_id = {outcome.content_id for outcome in outcomes}
        self._state.set_many(name, outcomes)
        for item in items:
            if item.content_id not in by_id:
                self._state.mark_failed(
                    name,
                    item.content_id,
                    PermanentFilterError("batch invariant violated: missing outcome", filter_name=name, content_ids=[item.content_id]),
                )

    # --------------------------------------------------------------- interne

    def _state_is(self, filter_name: str, content_id: str) -> FilterStatus:
        return self._state.filters[filter_name].items[content_id].status


__all__ = ["Worker", "ProcessResult"]
