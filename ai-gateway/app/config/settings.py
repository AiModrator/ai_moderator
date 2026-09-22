"""Configuration de l'AI Gateway (pydantic-settings).

Toutes les variables sont validées au démarrage. `ENCRYPTION_KEY`, `GATEWAY_API_KEY`,
`ADMIN_API_KEY` sont **requises** (absence → exit 1).
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """.env-sample → `.env` de base ; `.env.local` (chargé en premier, prioritaire)."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )

    # ---------- HTTP ----------
    http_port: int = Field(default=4000, ge=1, le=65535)

    # ---------- MongoDB ----------
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "ai_gateway"

    # ---------- Sécurité (requises) ----------
    encryption_key: str = Field(default="", min_length=44)  # Fernet key (base64, 32 bytes = 44 chars)
    gateway_api_key: str = Field(default="", min_length=1)
    admin_api_key: str = Field(default="", min_length=1)

    # ---------- Fournisseurs / réseau ----------
    request_timeout_sec: float = Field(default=30, ge=0)
    retry_max: int = Field(default=3, ge=0)
    retry_base_delay_ms: int = Field(default=500, ge=0)
    retry_multiplier: float = Field(default=2.0, ge=1.0)
    retry_max_delay_ms: int = Field(default=8000, ge=0)

    # ---------- Validation / fallback ----------
    response_retry: int = Field(default=1, ge=0)
    fallback_to_test_provider: bool = False

    # ---------- Requêtes de modération ----------
    max_items_per_request: int = Field(default=100, ge=1)
    default_account_id: str = "default"

    # ---------- Budget / usage ----------
    budget_default_monthly_limit: float = Field(default=100.0, ge=0)
    usage_retention_days: int = Field(default=90, ge=1)

    # ---------- Arrêt / logs ----------
    shutdown_timeout_sec: float = Field(default=15, ge=0)
    log_level: str = "INFO"
    log_format: str = "json"

    @field_validator("encryption_key", "gateway_api_key", "admin_api_key", mode="before")
    @classmethod
    def _required_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("variable requise manquante")
        return v.strip()

    @field_validator("log_format")
    @classmethod
    def _log_format(cls, v: str) -> str:
        v = v.lower()
        if v not in ("json", "console"):
            raise ValueError("LOG_FORMAT doit être 'json' ou 'console'")
        return v

    @field_validator("log_level")
    @classmethod
    def _log_level(cls, v: str) -> str:
        v = v.upper()
        if v not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ValueError("LOG_LEVEL invalide")
        return v

    @model_validator(mode="after")
    def _check_bounds(self) -> Settings:
        if self.retry_base_delay_ms > self.retry_max_delay_ms:
            raise ValueError("RETRY_BASE_DELAY_MS doit être <= RETRY_MAX_DELAY_MS")
        return self


__all__ = ["Settings"]
