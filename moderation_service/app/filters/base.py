"""Classes de base des filtres (main.md §4.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Literal

from app.schemas.enums import RiskClass
from app.schemas.job import ContentItem
from app.schemas.result import FilterContext, FilterOutcome


class BaseFilter(ABC):
    """Interface commune à tout filtre (item ou batch)."""

    NAME: ClassVar[str] = ""
    HANDLED_CLASSES: ClassVar[frozenset[RiskClass]] = frozenset()
    KIND: ClassVar[Literal["item", "batch"]]
    TIMEOUT_SEC: ClassVar[float] = 10.0

    def is_applicable(self, item: ContentItem) -> bool:
        """False → outcome SKIPPED sans exécution (main.md §4.1)."""
        return True


class ItemFilter(BaseFilter):
    """Filtre élémentaire : traite un item à la fois."""

    KIND: ClassVar[Literal["item", "batch"]] = "item"

    @abstractmethod
    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        """Évalue un item. Ne capture pas ses propres erreurs d'infrastructure."""


class BatchFilter(BaseFilter):
    """Filtre par lot : évalue un ensemble d'items.

    Invariant : renvoie exactement UN `FilterOutcome` par item reçu, même en cas
    d'erreur partielle (les items réussis COMPLETED, les autres via `content_ids`
    lèvent une `TransientFilterError`/`PermanentFilterError`).
    """

    KIND: ClassVar[Literal["item", "batch"]] = "batch"

    @abstractmethod
    async def evaluate_batch(self, items: list[ContentItem], ctx: FilterContext) -> list[FilterOutcome]:
        """Évalue un lot d'items — voir invariant ci-dessus."""


__all__ = ["BaseFilter", "ItemFilter", "BatchFilter"]
