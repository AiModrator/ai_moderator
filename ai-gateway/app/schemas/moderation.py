"""Schémas de l'endpoint de modération (main.md §2.1).

`extra="forbid"` → aucun champ superflu accepté.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.config import STRICT_CONFIG
from app.schemas.enums import MediaType


class ModerationItem(BaseModel):
    """Un item dans la requête de modération."""

    model_config = STRICT_CONFIG

    id: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ModerationRequest(BaseModel):
    """Corps de requête `POST /v1/moderation/{riskClass}`."""

    model_config = STRICT_CONFIG

    account_id: str = Field(default="default", validation_alias="accountId", serialization_alias="accountId")
    media_type: MediaType = Field(validation_alias="mediaType", serialization_alias="mediaType")
    items: Annotated[list[ModerationItem], Field(min_length=1)]

    @field_validator("items", mode="after")
    @classmethod
    def _unique_ids(cls, items: list[ModerationItem]) -> list[ModerationItem]:
        ids = [item.id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("item ids must be unique")
        return items


class ResultItem(BaseModel):
    """Résultat d'un item : score [0,1], aucune sévérité."""

    model_config = STRICT_CONFIG

    id: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str | None = None


class ModerationResponse(BaseModel):
    """Corps de réponse de l'AI Gateway."""

    model_config = STRICT_CONFIG

    model: str
    results: list[ResultItem] = Field(default_factory=list)


__all__ = ["ModerationItem", "ModerationRequest", "ModerationResponse", "ResultItem"]
