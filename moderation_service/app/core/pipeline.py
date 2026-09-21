"""Sélection des filtres actifs — `PipelineBuilder` (main.md §4.2)."""

from __future__ import annotations

from app.filters.base import BaseFilter
from app.filters.registry import get_filters
from app.schemas.enums import RiskClass
from app.schemas.result import FilterContext


class PipelineBuilder:
    """Construit le pipeline pour un lot : filtres dont `HANDLED_CLASSES` croise `activeClasses`."""

    def __init__(self, registry: list[type[BaseFilter]] | None = None) -> None:
        self._registry = registry if registry is not None else get_filters()

    def build(
        self,
        active_classes: list[RiskClass] | set[RiskClass],
        disabled: set[str] | None = None,
    ) -> tuple[list[type[BaseFilter]], dict[str, set[RiskClass]]]:
        """Retourne `(pipeline, targets)`.

        - `pipeline` : classes de filtres sélectionnées (dans l'ordre du registre).
        - `targets[NAME]` : `F.HANDLED_CLASSES ∩ activeClasses` (§4.2).
        - Un filtre nommé dans `disabled` est exclu et donc absent du `filtersReport`.
        """
        disabled = disabled or set()
        active = set(active_classes)
        pipeline: list[type[BaseFilter]] = []
        targets: dict[str, set[RiskClass]] = {}
        for cls in self._registry:
            if cls.NAME in disabled:
                continue
            intersect = cls.HANDLED_CLASSES & active
            if intersect:
                pipeline.append(cls)
                targets[cls.NAME] = intersect
        return pipeline, targets

    @staticmethod
    def build_contexts(
        batch_id: str,
        community_ref: str,
        attempt: int,
        targets: dict[str, set[RiskClass]],
    ) -> dict[str, FilterContext]:
        """Matérialise un `FilterContext` par filtre (les cibles calculées par `build`)."""
        return {
            name: FilterContext(
                batch_id=batch_id,
                community_ref=community_ref,
                attempt=attempt,
                target_classes=classes,
            )
            for name, classes in targets.items()
        }


__all__ = ["PipelineBuilder"]
