"""Structures internes de résultat (main.md §3.5)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas import STRICT_CONFIG
from app.schemas.enums import FilterStatus, RiskClass, Source


class Detection(BaseModel):
    """Une détection émise par un filtre : classe, score ∈ [0,1], origine.

    Aucun champ de sévérité : le score brut est le seul signal transmis à
    l'Action Service.
    """

    model_config = STRICT_CONFIG

    risk_class: RiskClass = Field(validation_alias="class", serialization_alias="class")
    score: float = Field(ge=0.0, le=1.0)
    source: Source
    filter: str
    detail: str | None = None


class FilterOutcome(BaseModel):
    """Résultat d'un filtre pour UN item (COMPLETED | SKIPPED | FAILED)."""

    model_config = STRICT_CONFIG

    content_id: str
    status: FilterStatus
    detections: list[Detection] = []
    error: str | None = None


class FilterContext(BaseModel):
    """Contexte passé à chaque filtre (main.md §3.5)."""

    model_config = STRICT_CONFIG

    batch_id: str
    community_ref: str
    attempt: int
    target_classes: set[RiskClass]


__all__ = ["Detection", "FilterOutcome", "FilterContext"]
