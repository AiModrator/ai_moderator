"""`AIGatewayClient` — client HTTP vers l'AI Gateway (contrat `phase-04/main.md` §2.1).

Isolé derrière ce client : fan-out par classe, plafonnement par
`AI_MAX_PARALLEL_REQUESTS` (sémaphore), et traduction des erreurs HTTP vers la
hiérarchie `AIGatewayError` (§7). Aucun détail OpenAI/LiteLLM n'y transparaît :
POST JSON par classe, `score` ∈ [0,1], aucune sévérité.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence

import httpx
from pydantic import ValidationError

from app.errors import (
    AIGatewayBadRequestError,
    AIGatewayBadResponseError,
    AIGatewayBudgetExceededError,
    AIGatewayUnavailableError,
)
from app.schemas.ai_gateway import ModerationItem, ModerationRequest, ModerationResponse

_JSON_HEADERS = {"Content-Type": "application/json"}


class AIGatewayClient:
    """Client HTTP (httpx) pour l'endpoint de modération par classe."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str = "",
        timeout_sec: float = 30.0,
        max_parallel: int = 4,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.AsyncClient(base_url=self._base_url, timeout=timeout_sec, headers=headers)
        self._semaphore = asyncio.Semaphore(max_parallel)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def moderate(
        self,
        risk_class: str,
        media_type: str,
        items: Sequence[tuple[str, str]],
    ) -> ModerationResponse:
        """POST `/v1/moderation/{riskClass}` pour un lot d'items `(id, content)`.

        Concurrence plafonnée (`max_parallel`) ; erreurs HTTP/transport traduites
        en `AIGatewayError`.
        """
        payload = ModerationRequest(
            account_id="default",
            active_classes=[risk_class],  # type: ignore[arg-type]
            media_type=media_type,  # type: ignore[arg-type]
            items=[ModerationItem(id=item_id, content=content) for item_id, content in items],
        )
        async with self._semaphore:
            try:
                response = await self._http.post(
                    f"/v1/moderation/{risk_class}",
                    content=payload.model_dump_json(by_alias=True),
                    headers=_JSON_HEADERS,
                )
            except httpx.TimeoutException as exc:
                raise AIGatewayUnavailableError("gateway timeout", status_code=408) from exc
            except httpx.TransportError as exc:
                raise AIGatewayUnavailableError("gateway unreachable") from exc
        return self._parse_response(response)

    async def health(self) -> bool:
        """PING `/health` de la gateway : `{"status":"ok"}` → True, sinon False (jamais d'exception)."""
        try:
            response = await self._http.get("/health")
        except httpx.HTTPError:
            return False
        if response.status_code != 200:
            return False
        try:
            body = response.json()
        except json.JSONDecodeError:
            return False
        return isinstance(body, dict) and body.get("status") == "ok"

    def _parse_response(self, response: httpx.Response) -> ModerationResponse:
        if response.status_code == 200:
            try:
                body = response.json()
                return ModerationResponse.model_validate(body)
            except (json.JSONDecodeError, ValidationError) as exc:
                raise AIGatewayBadResponseError("malformed gateway response", status_code=200) from exc
        status = response.status_code
        if status == 402:
            raise AIGatewayBudgetExceededError("gateway budget exhausted", status_code=status)
        if status in (408, 429):
            raise AIGatewayUnavailableError("gateway rate-limited or timed out", status_code=status)
        if status == 502:
            raise AIGatewayBadResponseError("provider response non conform", status_code=status)
        if 500 <= status <= 599:
            raise AIGatewayUnavailableError("gateway upstream failure", status_code=status)
        if 400 <= status <= 499:
            raise AIGatewayBadRequestError("gateway rejected request", status_code=status)
        raise AIGatewayUnavailableError("unexpected gateway status", status_code=status)


__all__ = ["AIGatewayClient"]
