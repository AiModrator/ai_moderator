"""Tests unitaires de l'`AIGatewayClient` (mapping d'erreurs, timeout, fan-out) — Tâche 05."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from app.clients.ai_gateway import AIGatewayClient
from app.errors import (
    AIGatewayBadRequestError,
    AIGatewayBadResponseError,
    AIGatewayBudgetExceededError,
    AIGatewayUnavailableError,
)

GATEWAY = "http://gateway"
OK_RESPONSE = {"model": "m", "results": [{"id": "c-1", "score": 0.9, "reason": "raison"}]}


def _client(**kwargs) -> AIGatewayClient:
    return AIGatewayClient(GATEWAY, api_key="secret", **kwargs)


@pytest.mark.unit
@respx.mock
async def test_success_parses_response() -> None:
    respx.post(f"{GATEWAY}/v1/moderation/TOXICITY").mock(
        return_value=httpx.Response(200, json=OK_RESPONSE)
    )
    client = _client()
    try:
        parsed = await client.moderate("TOXICITY", "text", [("c-1", "hello")])
    finally:
        await client.aclose()
    assert parsed.model == "m"
    assert parsed.results[0].id == "c-1"
    assert parsed.results[0].score == 0.9
    assert respx.calls.call_count == 1


@pytest.mark.unit
@respx.mock
async def test_request_headers_and_body() -> None:
    route = respx.post(f"{GATEWAY}/v1/moderation/INSULT").mock(
        return_value=httpx.Response(200, json=OK_RESPONSE)
    )
    client = _client()
    try:
        await client.moderate("INSULT", "text", [("c-1", "idiot")])
    finally:
        await client.aclose()
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer secret"
    assert request.headers["Content-Type"] == "application/json"
    body = json.loads(request.content)
    assert body["accountId"] == "default"
    assert body["mediaType"] == "text"
    assert body["items"] == [{"id": "c-1", "content": "idiot"}]


@pytest.mark.unit
@respx.mock
@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (402, AIGatewayBudgetExceededError),
        (408, AIGatewayUnavailableError),
        (429, AIGatewayUnavailableError),
        (500, AIGatewayUnavailableError),
        (503, AIGatewayUnavailableError),
        (502, AIGatewayBadResponseError),
        (400, AIGatewayBadRequestError),
        (401, AIGatewayBadRequestError),
        (403, AIGatewayBadRequestError),
        (422, AIGatewayBadRequestError),
    ],
)
async def test_error_status_mapping(status: int, error_type: type) -> None:
    respx.post(f"{GATEWAY}/v1/moderation/TOXICITY").mock(
        return_value=httpx.Response(status, json={"error": "nope"})
    )
    client = _client()
    try:
        with pytest.raises(error_type) as excinfo:
            await client.moderate("TOXICITY", "text", [("c-1", "x")])
        assert excinfo.value.status_code == status
    finally:
        await client.aclose()


@pytest.mark.unit
async def test_timeout_is_unavailable() -> None:
    client = _client(timeout_sec=0.05)
    with patch.object(
        client._http,
        "post",
        new=AsyncMock(side_effect=httpx.ReadTimeout("timeout")),
    ):
        with pytest.raises(AIGatewayUnavailableError):
            await client.moderate("TOXICITY", "text", [("c-1", "x")])
    await client.aclose()


@pytest.mark.unit
async def test_transport_error_is_unavailable() -> None:
    client = _client()
    with patch.object(
        client._http,
        "post",
        new=AsyncMock(side_effect=httpx.ConnectError("connection refused")),
    ):
        with pytest.raises(AIGatewayUnavailableError):
            await client.moderate("TOXICITY", "text", [("c-1", "x")])
    await client.aclose()


@pytest.mark.unit
@respx.mock
async def test_malformed_json_is_bad_response() -> None:
    respx.post(f"{GATEWAY}/v1/moderation/TOXICITY").mock(
        return_value=httpx.Response(200, text="<html>not json</html>")
    )
    client = _client()
    try:
        with pytest.raises(AIGatewayBadResponseError):
            await client.moderate("TOXICITY", "text", [("c-1", "x")])
    finally:
        await client.aclose()


@pytest.mark.unit
@respx.mock
async def test_missing_results_key_is_bad_response() -> None:
    respx.post(f"{GATEWAY}/v1/moderation/TOXICITY").mock(
        return_value=httpx.Response(200, json={"model": "m"})
    )
    client = _client()
    try:
        with pytest.raises(AIGatewayBadResponseError):
            await client.moderate("TOXICITY", "text", [("c-1", "x")])
    finally:
        await client.aclose()


@pytest.mark.unit
@respx.mock
async def test_health_ok() -> None:
    respx.get(f"{GATEWAY}/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    client = _client()
    try:
        assert await client.health() is True
    finally:
        await client.aclose()


@pytest.mark.unit
@respx.mock
async def test_health_ko_and_errors() -> None:
    respx.get(f"{GATEWAY}/health").mock(return_value=httpx.Response(503, json={"status": "ko"}))
    client = _client()
    try:
        assert await client.health() is False
    finally:
        await client.aclose()
    respx.reset()
    respx.get(f"{GATEWAY}/health").mock(side_effect=httpx.ConnectError("refused"))
    client2 = _client()
    try:
        assert await client2.health() is False
    finally:
        await client2.aclose()


@pytest.mark.unit
@respx.mock
async def test_concurrency_capped_by_max_parallel() -> None:
    active = 0
    max_active = 0

    async def counting_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1
        item_id = json.loads(_request.content)["items"][0]["id"]
        return httpx.Response(200, json={"model": "m", "results": [{"id": item_id, "score": 0.5}]})

    respx.post(f"{GATEWAY}/v1/moderation/TOXICITY").mock(side_effect=counting_handler)
    client = _client(max_parallel=2)
    try:
        await asyncio.gather(
            *(client.moderate("TOXICITY", "text", [(f"c-{i}", "x")]) for i in range(4))
        )
    finally:
        await client.aclose()
    assert max_active == 2  # plafonné, mais exécuté en parallèle (2 observés)
