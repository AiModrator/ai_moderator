"""Documents MongoDB pour providers et modèles (main.md §3)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.config import STRICT_CONFIG
from app.schemas.enums import MediaType, RiskClass


class ProviderKind(StrEnum):
    """Type de fournisseur."""

    OPENROUTER = "openrouter"
    TEST = "test"


class ProviderDocument(BaseModel):
    """Provider dans MongoDB (`providers`)."""

    model_config = STRICT_CONFIG

    name: str
    kind: ProviderKind
    display_name: str = Field(validation_alias="displayName", serialization_alias="displayName")
    base_url: str = Field(validation_alias="baseUrl", serialization_alias="baseUrl")
    api_key_encrypted: str | None = Field(default=None, validation_alias="apiKeyEncrypted", serialization_alias="apiKeyEncrypted")
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), validation_alias="createdAt", serialization_alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), validation_alias="updatedAt", serialization_alias="updatedAt")


class ModelDocument(BaseModel):
    """Modèle dans le Model Registry (`models`)."""

    model_config = STRICT_CONFIG

    id: str
    provider: str
    model: str
    display_name: str = Field(validation_alias="displayName", serialization_alias="displayName")
    capabilities: list[MediaType] = Field(default_factory=list)
    tasks: list[RiskClass] = Field(default_factory=list)
    max_input_tokens: int = Field(default=32000, validation_alias="maxInputTokens", serialization_alias="maxInputTokens")
    max_output_tokens: int = Field(default=500, validation_alias="maxOutputTokens", serialization_alias="maxOutputTokens")
    cost_input: float = Field(default=0.0, ge=0, validation_alias="costInput", serialization_alias="costInput")
    cost_output: float = Field(default=0.0, ge=0, validation_alias="costOutput", serialization_alias="costOutput")
    priority: int = Field(default=10, ge=0)
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), validation_alias="createdAt", serialization_alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), validation_alias="updatedAt", serialization_alias="updatedAt")


class BudgetDocument(BaseModel):
    """Budget dans MongoDB (`budgets`)."""

    model_config = STRICT_CONFIG

    account_id: str = Field(validation_alias="accountId", serialization_alias="accountId")
    currency: str = "USD"
    monthly_limit: float = Field(validation_alias="monthlyLimit", serialization_alias="monthlyLimit")
    warning_threshold_pct: int = Field(validation_alias="warningThresholdPct", serialization_alias="warningThresholdPct")
    consumed: float = 0.0
    period_start: datetime = Field(default_factory=lambda: datetime.now(UTC), validation_alias="periodStart", serialization_alias="periodStart")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), validation_alias="updatedAt", serialization_alias="updatedAt")


__all__ = ["ProviderKind", "ProviderDocument", "ModelDocument", "BudgetDocument"]
