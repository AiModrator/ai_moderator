"""Schémas d'administration (main.md §2.2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.config import STRICT_CONFIG
from app.schemas.enums import MediaType, RiskClass
from app.schemas.providers import ProviderKind


class ProviderCreate(BaseModel):
    """Création d'un fournisseur (admin)."""

    model_config = STRICT_CONFIG

    name: str = Field(min_length=1)
    kind: ProviderKind
    display_name: str = Field(validation_alias="displayName", serialization_alias="displayName")
    base_url: str = Field(validation_alias="baseUrl", serialization_alias="baseUrl")
    api_key: str = Field(min_length=1, validation_alias="apiKey", serialization_alias="apiKey")
    enabled: bool = True


class ProviderUpdate(BaseModel):
    """Mise à jour d'un fournisseur (admin)."""

    model_config = STRICT_CONFIG

    display_name: str | None = Field(default=None, validation_alias="displayName", serialization_alias="displayName")
    base_url: str | None = Field(default=None, validation_alias="baseUrl", serialization_alias="baseUrl")
    api_key: str | None = Field(default=None, validation_alias="apiKey", serialization_alias="apiKey")
    enabled: bool | None = None


class ProviderRead(BaseModel):
    """Provider pour lecture admin (clé masquée)."""

    model_config = STRICT_CONFIG

    name: str
    kind: ProviderKind
    display_name: str = Field(validation_alias="displayName", serialization_alias="displayName")
    base_url: str = Field(validation_alias="baseUrl", serialization_alias="baseUrl")
    api_key_encrypted: str = Field(validation_alias="apiKeyEncrypted", serialization_alias="apiKeyEncrypted")
    enabled: bool
    created_at: datetime = Field(validation_alias="createdAt", serialization_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt", serialization_alias="updatedAt")


class ModelCreate(BaseModel):
    """Création/mise à jour d'un modèle (admin)."""

    model_config = STRICT_CONFIG

    id: str = Field(min_length=1)
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


class ModelRead(BaseModel):
    """Modèle pour lecture admin."""

    model_config = STRICT_CONFIG

    id: str
    provider: str
    model: str
    display_name: str = Field(validation_alias="displayName", serialization_alias="displayName")
    capabilities: list[MediaType]
    tasks: list[RiskClass]
    max_input_tokens: int = Field(validation_alias="maxInputTokens", serialization_alias="maxInputTokens")
    max_output_tokens: int = Field(validation_alias="maxOutputTokens", serialization_alias="maxOutputTokens")
    cost_input: float = Field(validation_alias="costInput", serialization_alias="costInput")
    cost_output: float = Field(validation_alias="costOutput", serialization_alias="costOutput")
    priority: int
    enabled: bool
    created_at: datetime = Field(validation_alias="createdAt", serialization_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt", serialization_alias="updatedAt")


class BudgetSetLimits(BaseModel):
    """Définition des limites de budget (admin)."""

    model_config = STRICT_CONFIG

    monthly_limit: float = Field(ge=0, validation_alias="monthlyLimit", serialization_alias="monthlyLimit")
    warning_threshold_pct: int = Field(default=80, ge=0, le=100, validation_alias="warningThresholdPct", serialization_alias="warningThresholdPct")


class BudgetRead(BaseModel):
    """Budget pour lecture admin."""

    model_config = STRICT_CONFIG

    account_id: str = Field(validation_alias="accountId", serialization_alias="accountId")
    currency: str
    monthly_limit: float = Field(validation_alias="monthlyLimit", serialization_alias="monthlyLimit")
    warning_threshold_pct: int = Field(validation_alias="warningThresholdPct", serialization_alias="warningThresholdPct")
    consumed: float
    period_start: datetime = Field(validation_alias="periodStart", serialization_alias="periodStart")
    updated_at: datetime = Field(validation_alias="updatedAt", serialization_alias="updatedAt")


class UsageAggregate(BaseModel):
    """Agrégation d'usage (admin)."""

    model_config = STRICT_CONFIG

    total_requests: int = Field(validation_alias="totalRequests", serialization_alias="totalRequests")
    total_input_tokens: int = Field(validation_alias="totalInputTokens", serialization_alias="totalInputTokens")
    total_output_tokens: int = Field(validation_alias="totalOutputTokens", serialization_alias="totalOutputTokens")
    total_cost: float = Field(validation_alias="totalCost", serialization_alias="totalCost")
    total_errors: int = Field(validation_alias="totalErrors", serialization_alias="totalErrors")


class UsageAggregateByGroup(BaseModel):
    """Agrégation d'usage groupée."""

    model_config = STRICT_CONFIG

    group: str | None
    total_requests: int = Field(validation_alias="totalRequests", serialization_alias="totalRequests")
    total_input_tokens: int = Field(validation_alias="totalInputTokens", serialization_alias="totalInputTokens")
    total_output_tokens: int = Field(validation_alias="totalOutputTokens", serialization_alias="totalOutputTokens")
    total_cost: float = Field(validation_alias="totalCost", serialization_alias="totalCost")
    total_errors: int = Field(validation_alias="totalErrors", serialization_alias="totalErrors")


__all__ = [
    "ProviderCreate",
    "ProviderUpdate",
    "ProviderRead",
    "ModelCreate",
    "ModelRead",
    "BudgetSetLimits",
    "BudgetRead",
    "UsageAggregate",
    "UsageAggregateByGroup",
]
