"""Tests du `BatchState` (transitions, retryState round-trip) — Tâche 02."""

from __future__ import annotations

import pytest

from app.errors import PermanentFilterError, TransientFilterError
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.result import Detection, FilterOutcome
from app.schemas.state import BatchState, RetryState
from tests.fixtures.payloads import make_item, make_payload


def _state(max_retries: int = 3) -> BatchState:
    return BatchState.new(make_payload(active_classes=[RiskClass.TOXICITY, RiskClass.SCAM]), max_retries=max_retries)


def _detection(score: float = 0.9) -> Detection:
    return Detection(
        risk_class=RiskClass.TOXICITY,
        score=score,
        source=Source.TEXT,
        filter="AlwaysDetectFilter",
        detail="test",
    )


@pytest.mark.unit
def test_new_initializes_empty_filters() -> None:
    state = _state()
    assert state.attempt == 0
    assert state.filters == {}


@pytest.mark.unit
def test_ensure_filter_creates_pending_items() -> None:
    state = _state()
    state.ensure_filter("AlwaysDetectFilter", ["c-1", "c-2"])
    assert set(state.filters["AlwaysDetectFilter"].items) == {"c-1", "c-2"}
    assert all(
        s.status == FilterStatus.PENDING for s in state.filters["AlwaysDetectFilter"].items.values()
    )


@pytest.mark.unit
def test_ensure_filter_preserves_existing() -> None:
    state = _state()
    state.ensure_filter("AlwaysDetectFilter", ["c-1"])
    state.set(
        "AlwaysDetectFilter",
        FilterOutcome(content_id="c-1", status=FilterStatus.COMPLETED, detections=[_detection()]),
    )
    state.ensure_filter("AlwaysDetectFilter", ["c-1", "c-2"])
    item = state.filters["AlwaysDetectFilter"].items["c-1"]
    assert item.status == FilterStatus.COMPLETED
    assert state.filters["AlwaysDetectFilter"].items["c-2"].status == FilterStatus.PENDING


@pytest.mark.unit
def test_set_completed_increments_attempts() -> None:
    state = _state()
    state.ensure_filter("AlwaysDetectFilter", ["c-1"])
    state.set(
        "AlwaysDetectFilter",
        FilterOutcome(content_id="c-1", status=FilterStatus.COMPLETED, detections=[_detection()]),
    )
    item = state.filters["AlwaysDetectFilter"].items["c-1"]
    assert item.status == FilterStatus.COMPLETED
    assert item.attempts == 1
    assert item.detections == [_detection()]


@pytest.mark.unit
def test_set_skipped_keeps_attempts_zero() -> None:
    state = _state()
    state.ensure_filter("AlwaysDetectFilter", ["c-1"])
    state.set("AlwaysDetectFilter", FilterOutcome(content_id="c-1", status=FilterStatus.SKIPPED))
    item = state.filters["AlwaysDetectFilter"].items["c-1"]
    assert item.status == FilterStatus.SKIPPED
    assert item.attempts == 0
    assert item.detections == []


@pytest.mark.unit
def test_mark_transient_then_unavailable_after_max() -> None:
    state = _state(max_retries=1)
    state.ensure_filter("AlwaysDetectFilter", ["c-1"])
    err = TransientFilterError("boom", filter_name="AlwaysDetectFilter", content_ids=["c-1"])
    state.mark_transient("AlwaysDetectFilter", "c-1", err)
    item = state.filters["AlwaysDetectFilter"].items["c-1"]
    assert item.status == FilterStatus.PENDING_RETRY
    assert item.attempts == 1
    assert item.last_error == "TransientFilterError: boom [c-1]"
    state.mark_transient("AlwaysDetectFilter", "c-1", err)
    assert item.status == FilterStatus.UNAVAILABLE
    assert item.attempts == 2


@pytest.mark.unit
def test_mark_failed() -> None:
    state = _state()
    state.ensure_filter("AlwaysDetectFilter", ["c-1"])
    state.mark_failed(
        "AlwaysDetectFilter",
        "c-1",
        PermanentFilterError("nope", filter_name="AlwaysDetectFilter", content_ids=["c-1"]),
    )
    item = state.filters["AlwaysDetectFilter"].items["c-1"]
    assert item.status == FilterStatus.FAILED
    assert item.attempts == 1
    assert "nope" in item.last_error


@pytest.mark.unit
def test_resolved_items_only_when_all_terminal() -> None:
    state = _state()
    state.ensure_filter("AlwaysDetectFilter", ["c-1", "c-2"])
    state.ensure_filter("BatchDetectFilter", ["c-1", "c-2"])
    # c-1 : COMPLETED + COMPLETED → résolu
    state.set("AlwaysDetectFilter", FilterOutcome(content_id="c-1", status=FilterStatus.COMPLETED, detections=[_detection()]))
    state.set("BatchDetectFilter", FilterOutcome(content_id="c-1", status=FilterStatus.COMPLETED))
    # c-2 : COMPLETED + PENDING → non résolu
    state.set("AlwaysDetectFilter", FilterOutcome(content_id="c-2", status=FilterStatus.COMPLETED))
    assert state.resolved_items() == ["c-1"]


@pytest.mark.unit
def test_to_retry_state_keeps_only_unresolved_and_preserves_detections() -> None:
    state = _state()
    state.ensure_filter("AlwaysDetectFilter", ["c-1", "c-2"])
    state.ensure_filter("BatchDetectFilter", ["c-1", "c-2"])
    detection = _detection()
    state.set("AlwaysDetectFilter", FilterOutcome(content_id="c-1", status=FilterStatus.COMPLETED, detections=[detection]))
    state.set("BatchDetectFilter", FilterOutcome(content_id="c-1", status=FilterStatus.COMPLETED))
    state.set("AlwaysDetectFilter", FilterOutcome(content_id="c-2", status=FilterStatus.COMPLETED, detections=[]))
    state.mark_transient("BatchDetectFilter", "c-2", TransientFilterError("x", filter_name="BatchDetectFilter", content_ids=["c-2"]))

    retry = state.to_retry_state(["c-2"], next_attempt=1)
    assert retry.attempt == 1
    assert "c-1" not in retry.filters["AlwaysDetectFilter"].items
    assert "c-1" not in retry.filters["BatchDetectFilter"].items
    always_c2 = retry.filters["AlwaysDetectFilter"].items["c-2"]
    assert always_c2.status == FilterStatus.COMPLETED
    assert always_c2.attempts == 1
    batch_c2 = retry.filters["BatchDetectFilter"].items["c-2"]
    assert batch_c2.status == FilterStatus.PENDING_RETRY


@pytest.mark.unit
def test_from_retry_round_trip() -> None:
    original = _state()
    original.ensure_filter("AlwaysDetectFilter", ["c-1", "c-2"])
    original.ensure_filter("BatchDetectFilter", ["c-1", "c-2"])
    detection = _detection(score=0.7)
    original.set("AlwaysDetectFilter", FilterOutcome(content_id="c-2", status=FilterStatus.COMPLETED, detections=[detection]))
    original.mark_transient("BatchDetectFilter", "c-2", TransientFilterError("t", filter_name="BatchDetectFilter", content_ids=["c-2"]))

    retry = original.to_retry_state(["c-2"], next_attempt=1)
    # job republié : payload restreint aux items non résolus (seulement c-2)
    restored = BatchState.from_retry(
        make_payload(items=[make_item(content_id="c-2")], active_classes=[RiskClass.TOXICITY, RiskClass.SCAM]),
        retry,
        max_retries=3,
    )
    assert restored.attempt == 1
    assert restored.active_classes == [RiskClass.TOXICITY, RiskClass.SCAM]
    restored.ensure_filter("AlwaysDetectFilter", ["c-2"])
    restored.ensure_filter("BatchDetectFilter", ["c-2"])
    restored_detection = restored.filters["AlwaysDetectFilter"].items["c-2"]
    assert restored_detection.status == FilterStatus.COMPLETED
    assert restored_detection.attempts == 1
    assert restored_detection.detections == [detection]
    assert restored.filters["BatchDetectFilter"].items["c-2"].status == FilterStatus.PENDING_RETRY


@pytest.mark.unit
def test_from_retry_none_creates_fresh_state() -> None:
    state = BatchState.from_retry(make_payload(), retry_state=None, max_retries=3)
    assert state.attempt == 0
    assert state.filters == {}
    assert state.first_job_id == ""


@pytest.mark.unit
def test_retry_state_schema_validation() -> None:
    retry = RetryState(attempt=1, first_job_id="job-1", filters={})
    assert retry.first_job_id == "job-1"
