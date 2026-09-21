"""Filtres de test — de vraies sous-classes de `ItemFilter`/`BatchFilter` (main.md §14).

Injectés dans `FILTER_REGISTRY` pour piloter le Worker / le WorkerPool dans les
tests unit et integration. Ce ne sont PAS des mocks.
"""

from __future__ import annotations

import asyncio

from app.errors import PermanentFilterError, TransientFilterError
from app.filters.base import BatchFilter, ItemFilter
from app.filters.registry import register_filter
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.result import Detection, FilterContext, FilterOutcome


@register_filter
class AlwaysDetectFilter(ItemFilter):
    """Détecte chaque classe cible avec un score fixe → COMPLETED."""

    NAME = "AlwaysDetectFilter"
    HANDLED_CLASSES = frozenset({RiskClass.TOXICITY})
    TIMEOUT_SEC = 2.0

    def __init__(self, score: float = 0.9, detail: str = "fixture:always") -> None:
        self.score = score
        self.detail = detail

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        detections = [
            Detection(
                risk_class=risk_class,
                score=self.score,
                source=Source.TEXT,
                filter=self.NAME,
                detail=self.detail,
            )
            for risk_class in sorted(ctx.target_classes)
        ]
        return FilterOutcome(
            content_id=item.content_id,
            status=FilterStatus.COMPLETED,
            detections=detections,
        )


@register_filter
class PermanentFailFilter(ItemFilter):
    """Lève toujours une `PermanentFilterError` → FAILED."""

    NAME = "PermanentFailFilter"
    HANDLED_CLASSES = frozenset({RiskClass.SEXUAL})
    TIMEOUT_SEC = 2.0

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        raise PermanentFilterError(
            "fixture:permanent_failure",
            filter_name=self.NAME,
            content_ids=[item.content_id],
        )


@register_filter
class FailOnceThenSucceedFilter(ItemFilter):
    """Échoue en transitoire au 1er appel (global), réussit ensuite.

    État au niveau classe : persiste entre instances et passage de retry afin
    de tester « échec transitoire → PENDING_RETRY → succès au retry ».
    """

    NAME = "FailOnceThenSucceedFilter"
    HANDLED_CLASSES = frozenset({RiskClass.INSULT})
    TIMEOUT_SEC = 2.0

    _failure_budget = 1

    @classmethod
    def reset(cls) -> None:
        cls._failure_budget = 1

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        if self._failure_budget > 0:
            self.__class__._failure_budget -= 1
            raise TransientFilterError(
                "fixture:transient_failure",
                filter_name=self.NAME,
                content_ids=[item.content_id],
            )
        detection = Detection(
            risk_class=RiskClass.INSULT,
            score=0.8,
            source=Source.TEXT,
            filter=self.NAME,
            detail="fixture:success_after_retry",
        )
        return FilterOutcome(
            content_id=item.content_id,
            status=FilterStatus.COMPLETED,
            detections=[detection],
        )


@register_filter
class SkipFilter(ItemFilter):
    """Jamais applicable → l'item passe SKIPPED sans exécution."""

    NAME = "SkipFilter"
    HANDLED_CLASSES = frozenset({RiskClass.ADVERTISING})
    TIMEOUT_SEC = 2.0

    def is_applicable(self, item: ContentItem) -> bool:
        return False

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        raise RuntimeError("SkipFilter must never be evaluated (is_applicable = False)")


@register_filter
class SlowFilter(ItemFilter):
    """Filtre lent (délai configurable) pour tester le WorkerPool."""

    NAME = "SlowFilter"
    HANDLED_CLASSES = frozenset({RiskClass.VIOLENCE})
    TIMEOUT_SEC = 5.0

    _active = 0
    _max_active = 0

    def __init__(self, delay_sec: float = 0.3) -> None:
        self.delay_sec = delay_sec

    @classmethod
    def reset(cls) -> None:
        cls._active = 0
        cls._max_active = 0

    @classmethod
    def peak_active(cls) -> int:
        return cls._max_active

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        self.__class__._active += 1
        self.__class__._max_active = max(self.__class__._max_active, self.__class__._active)
        try:
            await asyncio.sleep(self.delay_sec)
            return FilterOutcome(content_id=item.content_id, status=FilterStatus.COMPLETED)
        finally:
            self.__class__._active -= 1


@register_filter
class BatchDetectFilter(BatchFilter):
    """BatchFilter : COMPLETED avec détection si le texte contient `scam`."""

    NAME = "BatchDetectFilter"
    HANDLED_CLASSES = frozenset({RiskClass.SCAM})
    TIMEOUT_SEC = 2.0

    async def evaluate_batch(
        self, items: list[ContentItem], ctx: FilterContext
    ) -> list[FilterOutcome]:
        outcomes: list[FilterOutcome] = []
        for item in items:
            detections: list[Detection] = []
            if item.text and "scam" in item.text.lower():
                detections.append(
                    Detection(
                        risk_class=RiskClass.SCAM,
                        score=0.7,
                        source=Source.TEXT,
                        filter=self.NAME,
                        detail="fixture:scam_keyword",
                    )
                )
            outcomes.append(
                FilterOutcome(
                    content_id=item.content_id,
                    status=FilterStatus.COMPLETED,
                    detections=detections,
                )
            )
        return outcomes


__all__ = [
    "AlwaysDetectFilter",
    "PermanentFailFilter",
    "FailOnceThenSucceedFilter",
    "SkipFilter",
    "SlowFilter",
    "BatchDetectFilter",
]
