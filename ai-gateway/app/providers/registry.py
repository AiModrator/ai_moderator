"""Registre des adaptateurs de fournisseurs (main.md §5.1)."""

from __future__ import annotations

from typing import Any

from app.config.settings import Settings
from app.providers.base import RetryPolicy
from app.providers.openrouter import OpenRouterAdapter
from app.providers.test_provider import TestProviderAdapter

PROVIDER_ADAPTERS: dict[str, type] = {
    "openrouter": OpenRouterAdapter,
    "test": TestProviderAdapter,
}


def build_adapter(
    kind: str,
    config: Any,  # ProviderDocument
    http_client: Any,  # httpx.AsyncClient
    settings: Settings,
) -> Any:
    """Construit l'adaptateur pour un `kind` donné."""
    if kind not in PROVIDER_ADAPTERS:
        raise ValueError(f"Unknown provider kind: {kind}")
    adapter_cls = PROVIDER_ADAPTERS[kind]
    retry = RetryPolicy(
        base_delay_ms=settings.retry_base_delay_ms,
        multiplier=settings.retry_multiplier,
        max_delay_ms=settings.retry_max_delay_ms,
        max_retries=settings.retry_max,
    )
    return adapter_cls(config, http_client, retry)


__all__ = ["PROVIDER_ADAPTERS", "build_adapter"]
