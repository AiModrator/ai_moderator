"""Schémas de la file `decisionQueue` (contrat inter-services, main.md §3.4)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas import STRICT_CONFIG
from app.schemas.enums import ContentType, FilterStatus, RiskClass, Source
from app.schemas.result import Detection


class DecisionStatus(StrEnum):
    """Statut global d'un contenu : COMPLETE ou PARTIAL (§3.4)."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"


class ContentRef(BaseModel):
    """Référence du contenu publiée vers `decisionQueue` (sans texte ni URLs)."""

    model_config = STRICT_CONFIG

    content_id: str
    content_type: ContentType
    user_ref: str
    timestamp: datetime


class AggregatedDetection(BaseModel):
    """Détection agrégée par classe : score max, sources et preuves (main.md §8)."""

    model_config = STRICT_CONFIG

    risk_class: RiskClass = Field(validation_alias="class", serialization_alias="class")
    score: float = Field(ge=0.0, le=1.0)
    sources: list[Source]
    evidence: list[Detection]


class FilterReport(BaseModel):
    """Rapport d'un filtre pour un contenu (§3.4 `filtersReport`)."""

    model_config = STRICT_CONFIG

    filter: str
    status: FilterStatus
    attempts: int
    error: str | None = None


class DecisionJob(BaseModel):
    """Job `decide` de `decisionQueue` — un par contenu résolu."""

    model_config = STRICT_CONFIG

    batch_id: str
    community_ref: str
    content: ContentRef
    active_classes: list[RiskClass]
    status: DecisionStatus
    detections: list[AggregatedDetection] = []
    filters_report: list[FilterReport] = []
    moderated_at: datetime
    processing_ms: int = Field(ge=0)


__all__ = ["DecisionStatus", "ContentRef", "AggregatedDetection", "FilterReport", "DecisionJob"]
