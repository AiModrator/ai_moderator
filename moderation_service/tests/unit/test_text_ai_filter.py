"""Tests unitaires de `TextAIFilter` (sous-lots, fan-out par classe, erreurs) — Tâche 05."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.clients.ai_gateway import AIGatewayClient
from app.errors import PermanentFilterError, TransientFilterError
from app.filters.text_ai_filter import TextAIFilter
from app.schemas.enums import FilterStatus, RiskClass
from tests.fixtures.payloads import make_context, make_item

GATEWAY = "http://gateway"


def _result(content_id: str, score: float, reason: str = "fr") -> dict:
    return {"id": content_id, "score": score, "reason": reason}


def _filter(*, min_chars: int = 2, batch_size: int = 2, max_chars: int = 4000) -> TextAIFilter:
    client = AIGatewayClient(GATEWAY, api_key="k", max_parallel=4)
    return TextAIFilter(client, min_chars=min_chars, batch_size=batch_size, max_chars_per_item=max_chars)


def _route_for(risk_class: str, handler) -> None:
    respx.post(f"{GATEWAY}/v1/moderation/{risk_class}").mock(side_effect=handler)


def _static(risk_class: str, results: list[dict]) -> None:
    _route_for(risk_class, lambda _request: httpx.Response(200, json={"model": "m", "results": results}))


@pytest.mark.unit
@respx.mock
async def test_success_full_fanout_and_subbatches() -> None:
    """3 items, 2 classes, batch_size=2 → 4 appels (2 sous-lots × 2 classes)."""
    items = [make_item(content_id=f"c-{i}", text="hello world " * 1) for i in range(1, 4)]
    seen: list[list[str]] = []

    def toxic_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        ids = [entry["id"] for entry in body["items"]]
        seen.append(ids)
        results = []
        for entry in body["items"]:
            score = {"c-1": 0.9, "c-2": 0.0, "c-3": 0.3}[entry["id"]]
            results.append(_result(entry["id"], score))
        return httpx.Response(200, json={"model": "m", "results": results})

    def insult_handler(request: httpx.Request) -> httpx.Response:
        results = []
        for entry in json.loads(request.content)["items"]:
            score = {"c-1": 0.0, "c-2": 0.8, "c-3": 0.1}[entry["id"]]
            results.append(_result(entry["id"], score))
        return httpx.Response(200, json={"model": "m", "results": results})

    _route_for("TOXICITY", toxic_handler)
    _route_for("INSULT", insult_handler)

    filter_ = _filter()
    try:
        outcomes = await filter_.evaluate_batch(items, make_context(target_classes={RiskClass.TOXICITY, RiskClass.INSULT}))
    finally:
        await filter_._client.aclose()
    respx.reset()

    assert sorted(seen) == [["c-1", "c-2"], ["c-3"]]
    assert [o.status for o in outcomes] == [FilterStatus.COMPLETED] * 3

    by_id = {o.content_id: o for o in outcomes}
    assert {d.risk_class: d.score for d in by_id["c-1"].detections} == {RiskClass.TOXICITY: 0.9}
    assert {d.risk_class: d.score for d in by_id["c-2"].detections} == {RiskClass.INSULT: 0.8}
    assert {d.risk_class: d.score for d in by_id["c-3"].detections} == {RiskClass.TOXICITY: 0.3, RiskClass.INSULT: 0.1}
    assert all(d.filter == "TextAIFilter" for o in outcomes for d in o.detections)


@pytest.mark.unit
@respx.mock
async def test_short_and_none_text_skipped() -> None:
    items = [
        make_item(content_id="c-1", text="hello world"),
        make_item(content_id="c-2", text="a"),
        make_item(content_id="c-3", text=None, attachments=[{"type": "image", "url": "http://img/x.png"}]),
    ]
    _static("TOXICITY", [_result("c-1", 0.9)])
    filter_ = _filter()
    try:
        outcomes = await filter_.evaluate_batch(items, make_context())
    finally:
        await filter_._client.aclose()
    assert {o.content_id: o.status for o in outcomes} == {
        "c-1": FilterStatus.COMPLETED,
        "c-2": FilterStatus.SKIPPED,
        "c-3": FilterStatus.SKIPPED,
    }


@pytest.mark.unit
@respx.mock
async def test_missing_result_triggers_transient_for_that_item() -> None:
    items = [make_item(content_id=f"c-{i}", text="hello world") for i in range(1, 4)]
    _static("TOXICITY", [_result("c-1", 0.9), _result("c-3", 0.2)])  # c-2 absent
    filter_ = _filter(batch_size=10)
    try:
        with pytest.raises(TransientFilterError) as excinfo:
            await filter_.evaluate_batch(items, make_context())
        assert excinfo.value.content_ids == ["c-2"]
        partial = excinfo.value.partial_outcomes
        assert {o.content_id for o in partial} == {"c-1", "c-3"}
        assert all(o.status == FilterStatus.COMPLETED for o in partial)
    finally:
        await filter_._client.aclose()


@pytest.mark.unit
@respx.mock
async def test_unknown_result_id_ignored() -> None:
    items = [make_item(content_id=f"c-{i}", text="hello world") for i in range(1, 4)]
    _static("TOXICITY", [_result("c-1", 0.9), _result("c-2", 0.4), _result("c-3", 0.1), _result("ghost", 0.9)])
    filter_ = _filter(batch_size=10)
    try:
        outcomes = await filter_.evaluate_batch(items, make_context())
    finally:
        await filter_._client.aclose()
    assert all(o.status == FilterStatus.COMPLETED for o in outcomes)
    assert len(outcomes[0].detections) == 1


@pytest.mark.unit
@respx.mock
async def test_zero_score_no_detection() -> None:
    items = [make_item(content_id="c-1", text="hello world")]
    _static("TOXICITY", [_result("c-1", 0.0, reason="clean")])
    filter_ = _filter(batch_size=10)
    try:
        outcomes = await filter_.evaluate_batch(items, make_context())
    finally:
        await filter_._client.aclose()
    assert outcomes[0].status == FilterStatus.COMPLETED
    assert outcomes[0].detections == []


@pytest.mark.unit
@respx.mock
async def test_transient_http_error_on_all_classes() -> None:
    items = [make_item(content_id=f"c-{i}", text="hello world") for i in range(1, 4)]
    _route_for("TOXICITY", lambda _r: httpx.Response(503, json={"error": "down"}))
    _route_for("INSULT", lambda _r: httpx.Response(500, json={"error": "boom"}))
    filter_ = _filter(batch_size=10)
    try:
        with pytest.raises(TransientFilterError) as excinfo:
            await filter_.evaluate_batch(items, make_context(target_classes={RiskClass.TOXICITY, RiskClass.INSULT}))
        assert set(excinfo.value.content_ids) == {"c-1", "c-2", "c-3"}
    finally:
        await filter_._client.aclose()


@pytest.mark.unit
@respx.mock
async def test_permanent_bad_request_error() -> None:
    items = [make_item(content_id=f"c-{i}", text="hello world") for i in range(1, 4)]
    _route_for("TOXICITY", lambda _r: httpx.Response(400, json={"error": "bad"}))
    filter_ = _filter(batch_size=10)
    try:
        with pytest.raises(PermanentFilterError) as excinfo:
            await filter_.evaluate_batch(items, make_context())
        assert set(excinfo.value.content_ids) == {"c-1", "c-2", "c-3"}
    finally:
        await filter_._client.aclose()


@pytest.mark.unit
@respx.mock
async def test_budget_exceeded_is_transient() -> None:
    items = [make_item(content_id="c-1", text="hello world")]
    _route_for("TOXICITY", lambda _r: httpx.Response(402, json={"error": "quota"}))
    filter_ = _filter(batch_size=10)
    try:
        with pytest.raises(TransientFilterError) as excinfo:
            await filter_.evaluate_batch(items, make_context())
        assert excinfo.value.content_ids == ["c-1"]
    finally:
        await filter_._client.aclose()


@pytest.mark.unit
@respx.mock
async def test_no_applicable_items_no_calls() -> None:
    items = [make_item(content_id="c-1", text="x"), make_item(content_id="c-2", text=None, attachments=[{"type": "video", "url": "http://img/v.mp4"}])]
    filter_ = _filter()
    try:
        outcomes = await filter_.evaluate_batch(items, make_context())
    finally:
        await filter_._client.aclose()
    assert respx.calls.call_count == 0
    assert all(o.status == FilterStatus.SKIPPED for o in outcomes)


@pytest.mark.unit
@respx.mock
async def test_truncation_applied_to_sent_content() -> None:
    long_text = "x" * 500
    item = make_item(content_id="c-1", text=long_text)
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["content"] = json.loads(request.content)["items"][0]["content"]
        return httpx.Response(200, json={"model": "m", "results": [_result("c-1", 0.5)]})

    _route_for("TOXICITY", handler)
    filter_ = _filter(max_chars=20)
    try:
        await filter_.evaluate_batch([item], make_context())
    finally:
        await filter_._client.aclose()
    assert captured["content"].startswith("x" * 20)
    assert captured["content"].endswith("[tronqué]")


@pytest.mark.unit
@respx.mock
async def test_no_overlapping_classes_all_skipped() -> None:
    items = [make_item(content_id="c-1", text="hello world")]
    filter_ = _filter()
    try:
        outcomes = await filter_.evaluate_batch(items, make_context(target_classes={RiskClass.OFF_TOPIC}))
    finally:
        await filter_._client.aclose()
    assert respx.calls.call_count == 0
    assert outcomes[0].status == FilterStatus.SKIPPED
