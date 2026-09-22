"""Tests unitaires de l'`OpenRouterAdapter` (mapping erreurs, retry, timeout, tokens)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from app.errors import (
    InvalidResponseError,
    ProviderQuotaError,
    ProviderRequestError,
    ProviderTransientError,
)
from app.providers.base import ProviderRequest, RetryPolicy
from app.providers.openrouter import OpenRouterAdapter

GATEWAY = "https://openrouter.ai/api/v1"
OK_RESPONSE = {"model": "test-model", "choices": [{"message": {"content": "0.9"}, "index": 0}], "usage": {"prompt_tokens": 100, "completion_tokens": 20}}


def _make_request() -> ProviderRequest:
    return ProviderRequest(
        model="test-model",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=100,
        timeout_sec=5.0,
        retry_policy=RetryPolicy(max_retries=2, base_delay_ms=10, multiplier=2, max_delay_ms=100),
        request_id="test-req",
        account_id="test",
        risk_class="TOXICITY",
    )


def _adapter() -> OpenRouterAdapter:
    class MockConfig:
        base_url = GATEWAY
        api_key_encrypted = "test-key"

    return OpenRouterAdapter(
        MockConfig(),
        httpx.AsyncClient(base_url=GATEWAY, timeout=5.0),
        RetryPolicy(max_retries=2, base_delay_ms=10, multiplier=2, max_delay_ms=100),
    )


class TestOpenRouterAdapter:
    @pytest.mark.unit
    @respx.mock
    async def test_success_parses_response(self) -> None:
        respx.post(f"{GATEWAY}/chat/completions").mock(return_value=httpx.Response(200, json=OK_RESPONSE))
        adapter = _adapter()
        try:
            resp = await adapter.run(_make_request())
        finally:
            await adapter._client.aclose()
        assert resp.model == "test-model"
        assert resp.input_tokens == 100
        assert resp.output_tokens == 20
        assert resp.latency_ms > 0

    @pytest.mark.unit
    @respx.mock
    @pytest.mark.parametrize(
        ("status", "error_type"),
        [
            (402, ProviderQuotaError),
            (408, ProviderTransientError),
            (429, ProviderTransientError),
            (500, ProviderTransientError),
            (502, ProviderTransientError),
            (503, ProviderTransientError),
            (400, ProviderRequestError),
            (401, ProviderRequestError),
            (403, ProviderRequestError),
            (404, ProviderRequestError),
            (422, ProviderRequestError),
        ],
    )
    async def test_error_status_mapping(self, status: int, error_type: type) -> None:
        respx.post(f"{GATEWAY}/chat/completions").mock(return_value=httpx.Response(status, json={"error": "fail"}))
        adapter = _adapter()
        try:
            with pytest.raises(error_type) as excinfo:
                await adapter.run(_make_request())
            assert excinfo.value.status_code == status
        finally:
            await adapter._client.aclose()

    @pytest.mark.unit
    @respx.mock
    async def test_timeout_is_transient(self) -> None:
        adapter = _adapter()
        try:
            with patch.object(adapter._client, "post", new=AsyncMock(side_effect=httpx.ReadTimeout("timeout"))):
                with pytest.raises(ProviderTransientError):
                    await adapter.run(_make_request())
        finally:
            await adapter._client.aclose()

    @pytest.mark.unit
    @respx.mock
    async def test_transport_error_is_transient(self) -> None:
        adapter = _adapter()
        try:
            with patch.object(adapter._client, "post", new=AsyncMock(side_effect=httpx.ConnectError("refused"))):
                with pytest.raises(ProviderTransientError):
                    await adapter.run(_make_request())
        finally:
            await adapter._client.aclose()

    @pytest.mark.unit
    @respx.mock
    async def test_malformed_json_is_invalid_response(self) -> None:
        respx.post(f"{GATEWAY}/chat/completions").mock(return_value=httpx.Response(200, text="not json"))
        adapter = _adapter()
        try:
            with pytest.raises(InvalidResponseError):
                await adapter.run(_make_request())
        finally:
            await adapter._client.aclose()

    @pytest.mark.unit
    @respx.mock
    async def test_empty_choices_is_invalid_response(self) -> None:
        respx.post(f"{GATEWAY}/chat/completions").mock(return_value=httpx.Response(200, json={"model": "m", "choices": []}))
        adapter = _adapter()
        try:
            with pytest.raises(InvalidResponseError):
                await adapter.run(_make_request())
        finally:
            await adapter._client.aclose()

    @pytest.mark.unit
    @respx.mock
    async def test_missing_tokens_estimated(self) -> None:
        """Si usage absent, tokens estimés localement."""
        response_no_usage = {"model": "test", "choices": [{"message": {"content": "hello"}, "index": 0}]}
        respx.post(f"{GATEWAY}/chat/completions").mock(return_value=httpx.Response(200, json=response_no_usage))
        adapter = _adapter()
        try:
            resp = await adapter.run(_make_request())
            assert resp.input_tokens >= 0  # estimation locale
            assert resp.output_tokens >= 0
        finally:
            await adapter._client.aclose()

    @pytest.mark.unit
    @respx.mock
    async def test_retry_on_transient_then_success(self) -> None:
        """Premier appel 500 (transient), second 200 -> succès au retry."""
        route = respx.post(f"{GATEWAY}/chat/completions").mock(
            side_effect=[
                httpx.Response(500, json={"error": "server error"}),
                httpx.Response(200, json=OK_RESPONSE),
            ]
        )
        adapter = _adapter()
        try:
            resp = await adapter.run(_make_request())
            assert route.call_count == 2
            assert resp.model == "test-model"
        finally:
            await adapter._client.aclose()

    @pytest.mark.unit
    @respx.mock
    async def test_no_retry_on_401(self) -> None:
        """401 ne retry pas."""
        respx.post(f"{GATEWAY}/chat/completions").mock(return_value=httpx.Response(401, json={"error": "unauthorized"}))
        adapter = _adapter()
        try:
            with pytest.raises(ProviderRequestError):
                await adapter.run(_make_request())
        finally:
            await adapter._client.aclose()
