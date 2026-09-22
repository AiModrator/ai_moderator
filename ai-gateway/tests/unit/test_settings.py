"""Tests unitaires des Settings (main.md §11)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.settings import Settings


class TestSettingsDefaults:
    def test_defaults(self) -> None:
        s = Settings(
            encryption_key="a" * 44,
            gateway_api_key="g",
            admin_api_key="a",
        )
        assert s.http_port == 4000
        assert s.mongodb_uri == "mongodb://localhost:27017"
        assert s.mongodb_db == "ai_gateway"
        assert s.request_timeout_sec == 30
        assert s.retry_max == 3
        assert s.retry_base_delay_ms == 500
        assert s.retry_multiplier == 2.0
        assert s.retry_max_delay_ms == 8000
        assert s.response_retry == 1
        assert s.fallback_to_test_provider is False
        assert s.max_items_per_request == 100
        assert s.default_account_id == "default"
        assert s.budget_default_monthly_limit == 100.0
        assert s.usage_retention_days == 90
        assert s.shutdown_timeout_sec == 15
        assert s.log_level == "INFO"
        assert s.log_format == "json"


class TestSettingsRequiredKeys:
    def test_encryption_key_required(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Settings(
                encryption_key="",
                gateway_api_key="g",
                admin_api_key="a",
            )
        assert "encryption_key" in str(exc.value).lower()

    def test_gateway_api_key_required(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Settings(
                encryption_key="a" * 44,
                gateway_api_key="",
                admin_api_key="a",
            )
        assert "gateway_api_key" in str(exc.value).lower()

    def test_admin_api_key_required(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Settings(
                encryption_key="a" * 44,
                gateway_api_key="g",
                admin_api_key="",
            )
        assert "admin_api_key" in str(exc.value).lower()


class TestSettingsBounds:
    def test_http_port_bounds(self) -> None:
        with pytest.raises(ValidationError):
            Settings(
                encryption_key="a" * 44,
                gateway_api_key="g",
                admin_api_key="a",
                http_port=0,
            )
        with pytest.raises(ValidationError):
            Settings(
                encryption_key="a" * 44,
                gateway_api_key="g",
                admin_api_key="a",
                http_port=70000,
            )

    def test_retry_base_gt_max_delay(self) -> None:
        with pytest.raises(ValidationError):
            Settings(
                encryption_key="a" * 44,
                gateway_api_key="g",
                admin_api_key="a",
                retry_base_delay_ms=9000,
                retry_max_delay_ms=8000,
            )

    def test_log_format_invalid(self) -> None:
        with pytest.raises(ValidationError):
            Settings(
                encryption_key="a" * 44,
                gateway_api_key="g",
                admin_api_key="a",
                log_format="xml",
            )

    def test_log_level_invalid(self) -> None:
        with pytest.raises(ValidationError):
            Settings(
                encryption_key="a" * 44,
                gateway_api_key="g",
                admin_api_key="a",
                log_level="TRACE",
            )

    def test_retry_multiplier_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            Settings(
                encryption_key="a" * 44,
                gateway_api_key="g",
                admin_api_key="a",
                retry_multiplier=0.5,
            )
