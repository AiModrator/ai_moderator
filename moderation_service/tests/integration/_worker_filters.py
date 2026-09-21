"""Filtres de test WorkerPart réel : compteurs d'appels et retry "une fois puis succès".

Ce sont de vraies sous-classes `ItemFilter` (pas des mocks) ; leur état est
class-level et doit être réarmé via `reset()` avant usage.
"""

from __future__ import annotations

from app.errors import TransientFilterError
from app.filters.base import ItemFilter
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.result import Detection, FilterContext, FilterOutcome


class CountedDetectFilter(ItemFilter):
    """COMPLETED avec détection pour chaque classe cible ; compte ses appels."""

    NAME = "CountedDetectFilter"
    HANDLED_CLASSES = frozenset({RiskClass.TOXICITY})
    TIMEOUT_SEC = 2.0

    _calls = 0

    @classmethod
    def reset(cls) -> None:
        cls._calls = 0

    @classmethod
    def calls(cls) -> int:
        return cls._calls

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        self.__class__._calls += 1
        detections = [
            Detection(
                risk_class=risk_class,
                score=0.9,
                source=Source.TEXT,
                filter=self.NAME,
                detail="calls_filter",
            )
            for risk_class in sorted(ctx.target_classes)
        ]
        return FilterOutcome(content_id=item.content_id, status=FilterStatus.COMPLETED, detections=detections)


class RetryOnceFilter(ItemFilter):
    """Échoue en transitoire sur le budget initial, puis COMPLETED (INSULT 0.8)."""

    NAME = "RetryOnceFilter"
    HANDLED_CLASSES = frozenset({RiskClass.INSULT})
    TIMEOUT_SEC = 2.0

    _budget = 0
    _calls = 0

    @classmethod
    def reset(cls, budget: int = 1) -> None:
        cls._budget = budget
        cls._calls = 0

    @classmethod
    def calls(cls) -> int:
        return cls._calls

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        self.__class__._calls += 1
        if self._budget > 0:
            self.__class__._budget -= 1
            raise TransientFilterError(
                "worker_fixture:transient_once",
                filter_name=self.NAME,
                content_ids=[item.content_id],
            )
        return FilterOutcome(
            content_id=item.content_id,
            status=FilterStatus.COMPLETED,
            detections=[
                Detection(
                    risk_class=RiskClass.INSULT,
                    score=0.8,
                    source=Source.TEXT,
                    filter=self.NAME,
                    detail="worker_fixture:ok",
                )
            ],
        )


__all__ = ["CountedDetectFilter", "RetryOnceFilter"]
