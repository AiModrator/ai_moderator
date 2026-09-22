"""Tests unitaires du `TestProviderAdapter` (main.md §5.3)."""

from __future__ import annotations

import json

import pytest

from app.errors import ProviderTransientError
from app.providers.base import ProviderRequest, RetryPolicy
from app.providers.test_provider import TestProviderAdapter


class _TestProviderAdapter(TestProviderAdapter):
    """Wrapper pour éviter le warning pytest sur __init__."""
    pass


class TestTestProviderAdapter:
    def _make_request(self, content: str) -> ProviderRequest:
        return ProviderRequest(
            model="test-model",
            messages=[{"role": "user", "content": content}],
            max_tokens=100,
            timeout_sec=5.0,
            retry_policy=RetryPolicy(),
            request_id="test-req",
            account_id="test",
            risk_class="TOXICITY",
        )

    @pytest.mark.asyncio
    async def test_score_convention(self) -> None:
        adapter = _TestProviderAdapter(None, None, RetryPolicy())
        req = self._make_request("hello __SCORE:0.75__ world")
        resp = await adapter.run(req)
        data = json.loads(resp.raw_text)
        # Le score est dans choices[0].message.content qui est un JSON stringifié
        inner = json.loads(data["choices"][0]["message"]["content"])
        assert inner["score"] == 0.75

    @pytest.mark.asyncio
    async def test_error_convention(self) -> None:
        adapter = _TestProviderAdapter(None, None, RetryPolicy())
        req = self._make_request("__ERROR__")
        with pytest.raises(ProviderTransientError):
            await adapter.run(req)

    @pytest.mark.asyncio
    async def test_invalid_convention(self) -> None:
        adapter = _TestProviderAdapter(None, None, RetryPolicy())
        req = self._make_request("__INVALID__")
        resp = await adapter.run(req)
        assert resp.raw_text == "not valid json at all {{{"

    @pytest.mark.asyncio
    async def test_default_zero(self) -> None:
        adapter = _TestProviderAdapter(None, None, RetryPolicy())
        req = self._make_request("just normal text")
        resp = await adapter.run(req)
        data = json.loads(resp.raw_text)
        assert data["choices"][0]["message"]["content"] == "0"

    @pytest.mark.asyncio
    async def test_latency_non_zero(self) -> None:
        adapter = _TestProviderAdapter(None, None, RetryPolicy())
        req = self._make_request("test")
        resp = await adapter.run(req)
        assert resp.latency_ms > 0
