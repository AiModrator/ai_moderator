"""Tests unitaires de `ImageAIFilter` (agrégation, cap images, erreurs) — Tâche 05."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.clients.ai_gateway import AIGatewayClient
from app.errors import PermanentFilterError, TransientFilterError
from app.filters.image_ai_filter import ImageAIFilter
from app.schemas.enums import FilterStatus, RiskClass
from tests.fixtures.payloads import make_context, make_item

GATEWAY = "http://gateway"


def _filter(*, max_images: int = 4) -> ImageAIFilter:
    client = AIGatewayClient(GATEWAY, api_key="k", max_parallel=4)
    return ImageAIFilter(client, max_images_per_item=max_images)


def _route(risk_class: str, by_url: dict[str, float], reason: str = "r") -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        results = [{"id": entry["id"], "score": by_url.get(entry["id"], 0.0), "reason": reason} for entry in body["items"]]
        return httpx.Response(200, json={"model": "m", "results": results})

    respx.post(f"{GATEWAY}/v1/moderation/{risk_class}").mock(side_effect=handler)


@pytest.mark.unit
@respx.mock
async def test_success_aggregates_per_class_max() -> None:
    u1, u2 = "http://img/1.png", "http://img/2.png"
    item = make_item(
        content_id="c-1",
        text="une image publique",
        attachments=[
            {"type": "image", "url": u1},
            {"type": "image", "url": u2},
        ],
    )
    _route("SEXUAL", {u1: 0.9, u2: 0.0}, reason="nudité")
    _route("VIOLENCE", {u1: 0.2, u2: 0.8}, reason="coups")

    filter_ = _filter()
    try:
        outcomes = await filter_.evaluate_batch([item], make_context(target_classes={RiskClass.SEXUAL, RiskClass.VIOLENCE}))
    finally:
        await filter_._client.aclose()

    assert outcomes[0].status == FilterStatus.COMPLETED
    detections = {d.risk_class: d for d in outcomes[0].detections}
    assert set(detections) == {RiskClass.SEXUAL, RiskClass.VIOLENCE}
    assert detections[RiskClass.SEXUAL].score == 0.9
    assert "image#1" in detections[RiskClass.SEXUAL].detail
    assert detections[RiskClass.VIOLENCE].score == 0.8
    assert "image#2" in detections[RiskClass.VIOLENCE].detail
    assert all(d.filter == "ImageAIFilter" for d in outcomes[0].detections)
    assert all(d.source.value == "image" for d in outcomes[0].detections)


@pytest.mark.unit
@respx.mock
async def test_video_ignored_and_noted() -> None:
    u1 = "http://img/1.png"
    item = make_item(
        content_id="c-1",
        text="une image publique",
        attachments=[
            {"type": "image", "url": u1},
            {"type": "video", "url": "http://img/v.mp4"},
        ],
    )
    _route("SEXUAL", {u1: 0.5})
    filter_ = _filter()
    try:
        outcomes = await filter_.evaluate_batch([item], make_context(target_classes={RiskClass.SEXUAL}))
    finally:
        await filter_._client.aclose()
    assert outcomes[0].status == FilterStatus.COMPLETED
    assert len(outcomes[0].detections) == 1
    assert "video unsupported" in outcomes[0].detections[0].detail
    assert "http://img/1.png" not in outcomes[0].detections[0].detail


@pytest.mark.unit
@respx.mock
async def test_image_cap_ignores_extra_and_notes() -> None:
    urls = [f"http://img/{i}.png" for i in range(3)]
    item = make_item(
        content_id="c-1",
        text="une image publique",
        attachments=[{"type": "image", "url": url} for url in urls],
    )
    _route("SEXUAL", {u: 0.6 for u in urls[:2]})
    filter_ = _filter(max_images=2)
    try:
        outcomes = await filter_.evaluate_batch([item], make_context(target_classes={RiskClass.SEXUAL}))
    finally:
        await filter_._client.aclose()
    assert outcomes[0].status == FilterStatus.COMPLETED
    assert len(outcomes[0].detections) == 1
    assert "1 image(s) ignored" in outcomes[0].detections[0].detail
    assert respx.calls.call_count >= 2


@pytest.mark.unit
@respx.mock
async def test_video_only_item_skipped_no_calls() -> None:
    item = make_item(
        content_id="c-1",
        text="une image publique",
        attachments=[{"type": "video", "url": "http://img/v.mp4"}],
    )
    filter_ = _filter()
    try:
        outcomes = await filter_.evaluate_batch([item], make_context(target_classes={RiskClass.VIOLENCE}))
    finally:
        await filter_._client.aclose()
    assert respx.calls.call_count == 0
    assert outcomes[0].status == FilterStatus.SKIPPED


@pytest.mark.unit
@respx.mock
async def test_zero_score_image_no_detection() -> None:
    u1 = "http://img/1.png"
    item = make_item(
        content_id="c-1",
        text="une image publique",
        attachments=[{"type": "image", "url": u1}],
    )
    _route("SEXUAL", {u1: 0.0})
    filter_ = _filter()
    try:
        outcomes = await filter_.evaluate_batch([item], make_context(target_classes={RiskClass.SEXUAL}))
    finally:
        await filter_._client.aclose()
    assert outcomes[0].status == FilterStatus.COMPLETED
    assert outcomes[0].detections == []


@pytest.mark.unit
@respx.mock
async def test_transient_error_marks_item_retry() -> None:
    u1, u2 = "http://img/1.png", "http://img/2.png"
    items = [
        make_item(content_id="c-1", text="x", attachments=[{"type": "image", "url": u1}]),
        make_item(content_id="c-2", text="x", attachments=[{"type": "image", "url": u2}]),
    ]
    respx.post(f"{GATEWAY}/v1/moderation/SEXUAL").mock(
        side_effect=[
            httpx.Response(200, json={"model": "m", "results": [{"id": u1, "score": 0.5, "reason": ""}]}),
            httpx.Response(503, json={"error": "down"}),
        ]
    )
    filter_ = _filter()
    try:
        with pytest.raises(TransientFilterError) as excinfo:
            await filter_.evaluate_batch(items, make_context(target_classes={RiskClass.SEXUAL}))
        assert excinfo.value.content_ids == ["c-2"]
        partial = excinfo.value.partial_outcomes
        assert [o.content_id for o in partial] == ["c-1"]
        assert partial[0].status == FilterStatus.COMPLETED
    finally:
        await filter_._client.aclose()


@pytest.mark.unit
@respx.mock
async def test_permanent_error_marks_item_failed() -> None:
    u1 = "http://img/1.png"
    item = make_item(
        content_id="c-1",
        text="x",
        attachments=[{"type": "image", "url": u1}],
    )
    respx.post(f"{GATEWAY}/v1/moderation/SEXUAL").mock(side_effect=lambda _r: httpx.Response(400, json={"error": "bad"}))
    filter_ = _filter()
    try:
        with pytest.raises(PermanentFilterError) as excinfo:
            await filter_.evaluate_batch([item], make_context(target_classes={RiskClass.SEXUAL}))
        assert excinfo.value.content_ids == ["c-1"]
    finally:
        await filter_._client.aclose()


@pytest.mark.unit
@respx.mock
async def test_no_overlapping_classes_skipped() -> None:
    u1 = "http://img/1.png"
    item = make_item(content_id="c-1", text="x", attachments=[{"type": "image", "url": u1}])
    filter_ = _filter()
    try:
        outcomes = await filter_.evaluate_batch([item], make_context(target_classes={RiskClass.TOXICITY}))
    finally:
        await filter_._client.aclose()
    assert respx.calls.call_count == 0
    assert outcomes[0].status == FilterStatus.SKIPPED
