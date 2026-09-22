"""Schémas de la file `contentQueue` (contrat inter-services, main.md §3.2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.schemas import STRICT_CONFIG
from app.schemas.enums import AttachmentType, ContentType, RiskClass
from app.schemas.state import RetryState


class Attachment(BaseModel):
    """Pièce jointe d'un contenu (image ou vidéo, URL http/https)."""

    model_config = STRICT_CONFIG

    type: AttachmentType
    url: HttpUrl


class ContentItem(BaseModel):
    """Un contenu unique à modérer."""

    model_config = STRICT_CONFIG

    content_id: str = Field(validation_alias="contentId", serialization_alias="contentId")
    content_type: ContentType = Field(validation_alias="contentType", serialization_alias="contentType")
    user_ref: str = Field(validation_alias="userRef", serialization_alias="userRef")
    timestamp: datetime = Field(serialization_alias="timestamp")
    text: str | None = Field(default=None, serialization_alias="text")
    attachments: list[Attachment] = Field(default_factory=list)

    @model_validator(mode="after")
    def _not_empty(self) -> ContentItem:
        if (self.text is None or not self.text.strip()) and not self.attachments:
            raise ValueError("text and attachments cannot both be empty")
        return self


class ContentBatchJob(BaseModel):
    """Payload complet d'un job `moderateBatch` de `contentQueue`."""

    model_config = STRICT_CONFIG

    batch_id: str = Field(validation_alias="batchId", serialization_alias="batchId")
    community_ref: str = Field(validation_alias="communityRef", serialization_alias="communityRef")
    active_classes: list[RiskClass] = Field(validation_alias="activeClasses", serialization_alias="activeClasses")
    items: list[ContentItem]
    retry_state: RetryState | None = Field(default=None, validation_alias="retryState", serialization_alias="retryState")

    @field_validator("batch_id")
    @classmethod
    def _batch_id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("batchId must not be empty")
        return value

    @field_validator("active_classes", mode="before")
    @classmethod
    def _active_classes_unique(cls, value: list[object]) -> list[object]:
        if not value:
            raise ValueError("activeClasses must not be empty")
        return list(dict.fromkeys(value))

    @field_validator("items")
    @classmethod
    def _items_valid(cls, items: list[ContentItem]) -> list[ContentItem]:
        if not items:
            raise ValueError("items must not be empty")
        ids = [item.content_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("contentId must be unique within the batch")
        return items


__all__ = ["Attachment", "ContentItem", "ContentBatchJob"]
