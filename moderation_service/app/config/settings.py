"""Configuration du service (pydantic-settings).

Toute valeur ajustable du service vit dans `.env-sample`/`.env` et est déclarée
ici. Une configuration incohérente (bornes violées) → ValidationError à la
construction, ce qui arrête le service avant le démarrage.
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: object) -> object:
    """Transforme une valeur CSV (``"a,b,c"``) en liste, sinon retourne telle quelle."""
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


class Settings(BaseSettings):
    """.env-sample → `.env` de base ; `.env.local` (chargé en premier, prioritaire)"""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )

    # ---------- Redis / BullMQ ----------
    redis_host: str = "localhost"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: str = ""
    content_queue_name: str = "contentQueue"
    decision_queue_name: str = "decisionQueue"

    # ---------- HTTP ----------
    http_port: int = Field(default=8000, ge=1, le=65535)

    # ---------- WorkerPool ----------
    worker_pool_min: int = Field(default=2, ge=0)
    worker_pool_initial: int = Field(default=4, ge=0)
    worker_pool_max: int = Field(default=32, ge=1)
    scale_step: int = Field(default=2, ge=1)
    scale_cooldown_sec: float = Field(default=10, ge=0)
    monitor_interval_sec: float = Field(default=5, ge=0.1)
    # Seuils d'auto-scaling (pourcentages 0-100)
    cpu_low_pct: float = Field(default=65, ge=0, le=100)
    cpu_high_pct: float = Field(default=85, ge=0, le=100)
    ram_low_pct: float = Field(default=70, ge=0, le=100)
    ram_high_pct: float = Field(default=80, ge=0, le=100)
    ram_critical_pct: float = Field(default=90, ge=0, le=100)

    # ---------- Retry sélectif (géré par le Worker, pas par BullMQ) ----------
    max_filter_retries: int = Field(default=3, ge=0)
    retry_base_delay_ms: int = Field(default=5000, ge=0)
    retry_max_delay_ms: int = Field(default=300_000, ge=0)

    # ---------- Lot / filtres ----------
    max_items_per_batch: int = Field(default=50, ge=1)
    filter_timeout_sec: float = Field(default=10, ge=0)
    filters_disabled: list[str] = Field(default_factory=list)

    # ---------- AI Gateway (contrat provisoire, phase 4/5) ----------
    ai_gateway_url: str = "http://localhost:4000"
    ai_gateway_api_key: str = ""
    ai_request_timeout_sec: float = Field(default=30, ge=0)
    ai_max_parallel_requests: int = Field(default=4, ge=1)
    ai_text_batch_size: int = Field(default=10, ge=1)
    ai_text_max_chars_per_item: int = Field(default=4000, ge=1)
    ai_text_min_chars: int = Field(default=2, ge=0)
    max_images_per_item: int = Field(default=4, ge=0)

    # ---------- SpamFilter (Redis) ----------
    spam_dup_window_sec: int = Field(default=3600, ge=1)
    spam_flood_window_sec: int = Field(default=60, ge=1)
    spam_flood_threshold: int = Field(default=10, ge=1)

    # ---------- LinkFilter ----------
    link_allowlist_domains: list[str] = Field(default_factory=list)
    link_suspicious_tlds: list[str] = Field(
        default_factory=lambda: ["zip", "mov", "tk", "top", "xyz", "gq", "ml", "cf", "click", "work"]
    )

    # ---------- LexiconFilter ----------
    lexicon_max_score: float = Field(default=0.85, ge=0, le=1)

    # ---------- Arrêt / logs / tests ----------
    shutdown_timeout_sec: float = Field(default=30, ge=0)
    log_level: str = "INFO"
    log_format: str = "json"
    test_queue_prefix: str = "test"

    @field_validator("filters_disabled", "link_allowlist_domains", "link_suspicious_tlds", mode="before")
    @classmethod
    def _csv_list(cls, value: object) -> object:
        return _split_csv(value)

    @model_validator(mode="after")
    def _check_bounds(self) -> Settings:
        if not (self.worker_pool_min <= self.worker_pool_initial <= self.worker_pool_max):
            raise ValueError(
                f"WORKER_POOL_MIN ({self.worker_pool_min}) <= WORKER_POOL_INITIAL ({self.worker_pool_initial}) "
                f"<= WORKER_POOL_MAX ({self.worker_pool_max}) must hold."
            )
        if not (self.cpu_low_pct < self.cpu_high_pct):
            raise ValueError("CPU_LOW_PCT must be < CPU_HIGH_PCT.")
        if not (self.ram_low_pct < self.ram_high_pct < self.ram_critical_pct):
            raise ValueError("RAM_LOW_PCT < RAM_HIGH_PCT < RAM_CRITICAL_PCT must hold.")
        if self.retry_base_delay_ms > self.retry_max_delay_ms:
            raise ValueError("RETRY_BASE_DELAY_MS must be <= RETRY_MAX_DELAY_MS.")
        return self


__all__ = ["Settings"]
