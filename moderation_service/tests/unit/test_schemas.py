"""Tests des contrats Pydantic (main.md §3) — Tâche 01."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.decision import DecisionJob
from app.schemas.enums import ContentType, RiskClass, Source
from app.schemas.job import ContentBatchJob
from app.schemas.result import Detection


def _valid_payload(retry_state: object = None) -> dict:
    return {
        "batchId": "batch-1",
        "communityRef": "community-A",
        "activeClasses": ["SPAM", "TOXICITY"],
        "items": [
            {
                "contentId": "c-1",
                "contentType": "comment",
                "userRef": "u-1",
                "timestamp": "2026-01-01T00:00:00Z",
                "text": "hello world",
                "attachments": [],
            }
        ],
        "retryState": retry_state,
    }


@pytest.mark.unit
def test_content_batch_job_valid() -> None:
    job = ContentBatchJob.model_validate(_valid_payload())
    assert job.batch_id == "batch-1"
    assert job.active_classes == [RiskClass.SPAM, RiskClass.TOXICITY]
    assert job.items[0].content_id == "c-1"
    assert job.retry_state is None
    # serialisation camelCase
    exported = job.model_dump(by_alias=True)
    assert exported["batchId"] == "batch-1"
    assert exported["activeClasses"] == ["SPAM", "TOXICITY"]


@pytest.mark.unit
def test_content_batch_job_rejects_empty_items() -> None:
    payload = _valid_payload()
    payload["items"] = []
    with pytest.raises(ValidationError):
        ContentBatchJob.model_validate(payload)


@pytest.mark.unit
def test_content_batch_job_rejects_duplicate_content_id() -> None:
    payload = _valid_payload()
    payload["items"].append(payload["items"][0].copy())
    with pytest.raises(ValidationError, match="contentId must be unique"):
        ContentBatchJob.model_validate(payload)


@pytest.mark.unit
def test_content_batch_job_rejects_empty_active_classes() -> None:
    payload = _valid_payload()
    payload["activeClasses"] = []
    with pytest.raises(ValidationError, match="activeClasses must not be empty"):
        ContentBatchJob.model_validate(payload)


@pytest.mark.unit
def test_content_batch_job_rejects_unknown_risk_class() -> None:
    payload = _valid_payload()
    payload["activeClasses"] = ["UNKNOWN"]
    with pytest.raises(ValidationError):
        ContentBatchJob.model_validate(payload)


@pytest.mark.unit
def test_content_batch_job_rejects_unknown_extra_field() -> None:
    payload = _valid_payload()
    payload["nope"] = "extra"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ContentBatchJob.model_validate(payload)


@pytest.mark.unit
def test_content_batch_job_rejects_non_http_attachment_url() -> None:
    payload = _valid_payload()
    payload["items"][0]["attachments"] = [{"type": "image", "url": "ftp://example.com/x.png"}]
    with pytest.raises(ValidationError):
        ContentBatchJob.model_validate(payload)


@pytest.mark.unit
def test_content_batch_job_rejects_both_text_and_attachments_empty() -> None:
    payload = _valid_payload()
    payload["items"][0]["text"] = None
    payload["items"][0]["attachments"] = []
    with pytest.raises(ValidationError, match="text and attachments cannot both be empty"):
        ContentBatchJob.model_validate(payload)


@pytest.mark.unit
def test_content_batch_job_accepts_attachment_only() -> None:
    payload = _valid_payload()
    payload["items"][0]["text"] = None
    payload["items"][0]["attachments"] = [
        {"type": "image", "url": "https://cdn.example.com/a.png"},
        {"type": "video", "url": "https://cdn.example.com/a.mp4"},
    ]
    job = ContentBatchJob.model_validate(payload)
    assert len(job.items[0].attachments) == 2


@pytest.mark.unit
def test_detection_fields_only() -> None:
    detection = Detection(
        risk_class=RiskClass.TOXICITY,
        score=0.91,
        source=Source.TEXT,
        filter="TextAIFilter",
        detail="insulte directe",
    )
    data = detection.model_dump()
    assert set(data.keys()) == {"risk_class", "score", "source", "filter", "detail"}
    assert "severity" not in data
    assert "severity" not in detection.model_dump(by_alias=True)
    exported = detection.model_dump(by_alias=True)
    assert exported["class"] == "TOXICITY"


@pytest.mark.unit
def test_detection_score_bounds() -> None:
    with pytest.raises(ValidationError):
        Detection(risk_class=RiskClass.TOXICITY, score=1.5, source=Source.TEXT, filter="F")
    with pytest.raises(ValidationError):
        Detection(risk_class=RiskClass.TOXICITY, score=-0.1, source=Source.TEXT, filter="F")


@pytest.mark.unit
def test_detection_score_equal_bounds_ok() -> None:
    Detection(risk_class=RiskClass.SEXUAL, score=0.0, source=Source.IMAGE, filter="F")
    Detection(risk_class=RiskClass.SEXUAL, score=1.0, source=Source.IMAGE, filter="F")


@pytest.mark.unit
def test_decision_job_roundtrip() -> None:
    job = DecisionJob(
        batch_id="b",
        community_ref="c",
        content={
            "contentId": "i",
            "contentType": ContentType.POST,
            "userRef": "u",
            "timestamp": "2026-01-01T00:00:00Z",
        },
        active_classes=[RiskClass.SPAM],
        status="COMPLETE",
        detections=[],
        filters_report=[],
        moderated_at="2026-01-01T00:00:01Z",
        processing_ms=5,
    )
    exported = job.model_dump(by_alias=True, mode="json")
    assert exported["content"]["contentId"] == "i"
    assert exported["moderatedAt"] == "2026-01-01T00:00:01Z"
    assert exported["processingMs"] == 5
