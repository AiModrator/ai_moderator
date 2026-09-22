"""Adaptateur OpenRouter (main.md §5.2)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.errors import (
    InvalidResponseError,
    ProviderQuotaError,
    ProviderRequestError,
    ProviderTransientError,
)
from app.providers.base import ProviderAdapter, ProviderRequest, ProviderResponse, RetryPolicy


class OpenRouterAdapter(ProviderAdapter):
    """Appel HTTP vers OpenRouter `POST /chat/completions`.

    - Auth `Authorization: Bearer <clé déchiffrée>`
    - Body : `model`, `messages`, `max_tokens`, `temperature=0`
    - Extraction `choices[0].message.content` + tokens via `usage.*`
    - Retry exponentiel sur 408/429/5xx/timeout/réseau
    - 400/401/403/404/422 → ProviderRequestError (jamais retry)
    - 402 → ProviderQuotaError (permanent)
    """

    KIND = "openrouter"

    def __init__(
        self,
        config: Any,  # ProviderDocument avec api_key_encrypted déjà déchiffrée
        client: httpx.AsyncClient,
        retry: RetryPolicy,
    ) -> None:
        super().__init__(config, client, retry)
        self._base_url = config.base_url.rstrip("/")
        self._api_key = config.api_key_encrypted  # déjà en clair (déchiffrée par repo)

    async def run(self, req: ProviderRequest) -> ProviderResponse:
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": req.model,
            "messages": req.messages,
            "max_tokens": req.max_tokens,
            "temperature": 0,
        }

        last_exc: Exception | None = None
        for attempt in range(self._retry.max_retries + 1):
            t0 = time.perf_counter()
            try:
                response = await self._client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=req.timeout_sec,
                )
                latency_ms = (time.perf_counter() - t0) * 1000

                if response.status_code == 200:
                    return self._parse_ok_response(response, req.model, latency_ms)

                # Mapping codes d'erreur
                if response.status_code in (400, 401, 403, 404, 422):
                    raise ProviderRequestError(
                        f"OpenRouter {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )
                if response.status_code == 402:
                    raise ProviderQuotaError(
                        f"OpenRouter quota exceeded: {response.text}",
                        status_code=response.status_code,
                    )
                # 408, 429, 5xx → retryable : on mémorise l'erreur pour retry
                last_exc = ProviderTransientError(
                    f"OpenRouter {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )

            except httpx.TimeoutException:
                latency_ms = (time.perf_counter() - t0) * 1000
                last_exc = ProviderTransientError("OpenRouter timeout", status_code=408)
            except httpx.TransportError as exc:
                latency_ms = (time.perf_counter() - t0) * 1000
                last_exc = ProviderTransientError(
                    f"OpenRouter transport error: {exc}", status_code=None
                )

            # Retry si pas la dernière tentative
            if attempt < self._retry.max_retries:
                delay_ms = self._retry.delay_for(attempt)
                await asyncio.sleep(delay_ms / 1000.0)
                continue

            # Épuisé
            raise last_exc or ProviderTransientError("OpenRouter max retries exceeded")

        # Ne devrait pas être atteint
        raise ProviderTransientError("OpenRouter unexpected exit")

    def _parse_ok_response(self, response: httpx.Response, fallback_model: str, latency_ms: float) -> ProviderResponse:
        try:
            data = response.json()
        except Exception as exc:
            raise InvalidResponseError(f"JSON invalide: {exc}", status_code=200) from exc

        choices = data.get("choices", [])
        if not choices:
            raise InvalidResponseError("Réponse sans 'choices'", status_code=200)

        msg = choices[0].get("message", {})
        raw_text = msg.get("content", "")
        model = data.get("model", fallback_model)

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Estimation locale si tokens absents
        if input_tokens == 0 and output_tokens == 0:
            input_tokens = self._estimate_input_tokens(req_messages=[])
            output_tokens = 0

        return ProviderResponse(
            raw_text=raw_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model=model,
        )

    def _estimate_input_tokens(self, req_messages: list[dict]) -> int:
        """Estimation grossière : 1 token ≈ 4 caractères."""
        total_chars = sum(len(m.get("content", "")) for m in req_messages)
        return max(1, (total_chars + 3) // 4)


__all__ = ["OpenRouterAdapter"]
