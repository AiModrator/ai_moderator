"""Contrat AI Gateway (référence `phase-04/main.md` §2.1) — score uniquement, aucune sévérité."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import STRICT_CONFIG

MediaType = Literal["text", "image"]


class ModerationItem(BaseModel):
    """Un item dans la requête de modération."""

    model_config = STRICT_CONFIG

    id: str = Field(min_length=1)
    content: str


class ModerationRequest(BaseModel):
    """Corps de requête `POST /v1/moderation/{riskClass}`."""

    model_config = STRICT_CONFIG

    account_id: str = Field(default="default", validation_alias="accountId", serialization_alias="accountId")
    media_type: MediaType = Field(validation_alias="mediaType", serialization_alias="mediaType")
    items: list[ModerationItem] = Field(min_length=1)


class ModerationResult(BaseModel):
    """Score d'intensité pour une classe — `score` ∈ [0,1], aucune sévérité."""

    model_config = STRICT_CONFIG

    id: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str | None = None


class ModerationResponse(BaseModel):
    """Corps de réponse de l'AI Gateway."""

    model_config = STRICT_CONFIG

    model: str
    results: list[ModerationResult]


__all__ = ["ModerationItem", "ModerationRequest", "ModerationResponse", "MediaType"]
