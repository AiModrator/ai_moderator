"""Tests du `Settings` : valeurs par défaut, bornes, parsing CSV (Tâche 01)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.settings import Settings


@pytest.mark.unit
def test_defaults() -> None:
    settings = Settings()
    assert settings.worker_pool_min == 2
    assert settings.worker_pool_initial == 4
    assert settings.worker_pool_max == 32
    assert settings.cpu_low_pct == 65
    assert settings.cpu_high_pct == 85
    assert settings.ram_critical_pct == 90
    assert settings.max_filter_retries == 3
    assert settings.max_items_per_batch == 50
    assert settings.lexicon_max_score == 0.85
    assert settings.ai_text_batch_size == 10
    assert settings.link_suspicious_tlds == ["zip", "mov", "tk", "top", "xyz", "gq", "ml", "cf", "click", "work"]


@pytest.mark.unit
def test_csv_lists_parsed() -> None:
    settings = Settings(
        filters_disabled="ImageAIFilter,LinkFilter",
        link_allowlist_domains="youtube.com, github.com",
    )
    assert settings.filters_disabled == ["ImageAIFilter", "LinkFilter"]
    assert settings.link_allowlist_domains == ["youtube.com", "github.com"]


@pytest.mark.unit
def test_csv_list_accepts_json_array() -> None:
    settings = Settings(link_allowlist_domains=["a.com", "b.com"])
    assert settings.link_allowlist_domains == ["a.com", "b.com"]


@pytest.mark.unit
def test_rejects_incoherent_pool() -> None:
    with pytest.raises(ValidationError, match="WORKER_POOL_MIN"):
        Settings(worker_pool_min=10, worker_pool_initial=5, worker_pool_max=20)
    with pytest.raises(ValidationError, match="WORKER_POOL_MIN"):
        Settings(worker_pool_min=2, worker_pool_initial=10, worker_pool_max=5)


@pytest.mark.unit
def test_rejects_incoherent_cpu() -> None:
    with pytest.raises(ValidationError, match="CPU_LOW_PCT"):
        Settings(cpu_low_pct=90, cpu_high_pct=80)


@pytest.mark.unit
def test_rejects_incoherent_ram() -> None:
    with pytest.raises(ValidationError, match="RAM_LOW_PCT"):
        Settings(ram_low_pct=85, ram_high_pct=90, ram_critical_pct=90)
    with pytest.raises(ValidationError, match="RAM_LOW_PCT"):
        Settings(ram_low_pct=60, ram_high_pct=50, ram_critical_pct=95)


@pytest.mark.unit
def test_rejects_retry_backoff_inverted() -> None:
    with pytest.raises(ValidationError, match="RETRY_BASE_DELAY_MS"):
        Settings(retry_base_delay_ms=300_000, retry_max_delay_ms=5_000)


@pytest.mark.unit
def test_rejects_percent_out_of_range() -> None:
    with pytest.raises(ValidationError):
        Settings(cpu_high_pct=101)
    with pytest.raises(ValidationError):
        Settings(ram_critical_pct=-1)


@pytest.mark.unit
def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(unknown_option=42)  # type: ignore[call-arg]
