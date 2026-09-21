"""Tests du `ResultAggregator` (main.md §8) — Tâche 02."""

from __future__ import annotations

import pytest

from app.core.aggregator import ResultAggregator
from app.errors import PermanentFilterError
from app.schemas.decision import DecisionStatus
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.result import Detection, FilterOutcome
from app.schemas.state import BatchState
from tests.fixtures.filters import AlwaysDetectFilter, PermanentFailFilter
from tests.fixtures.payloads import make_item, make_payload


def _state_with() -> BatchState:
    state = BatchState.new(
        make_payload(active_classes=[RiskClass.TOXICITY, RiskClass.SEXUAL]),
        max_retries=3,
    )
    state.ensure_filter("AlwaysDetectFilter", ["c-1"])
    state.ensure_filter("PermanentFailFilter", ["c-1"])
    return state


def _add_txt(state: BatchState, filter_name: str, content_id: str, score: float, source: Source) -> None:
    state.set(
        filter_name,
        FilterOutcome(
            content_id=content_id,
            status=FilterStatus.COMPLETED,
            detections=[
                Detection(
                    risk_class=RiskClass.TOXICITY,
                    score=score,
                    source=source,
                    filter=filter_name,
                    detail="evidence",
                )
            ],
        ),
    )


def _add_multi(state: BatchState, filter_name: str, content_id: str, *dets: Detection) -> None:
    state.set(
        filter_name,
        FilterOutcome(content_id=content_id, status=FilterStatus.COMPLETED, detections=list(dets)),
    )


@pytest.mark.unit
def test_aggregate_max_score_and_evidence_sorted() -> None:
    state = _state_with()
    _add_multi(
        state,
        "AlwaysDetectFilter",
        "c-1",
        Detection(risk_class=RiskClass.TOXICITY, score=0.9, source=Source.TEXT, filter="AlwaysDetectFilter", detail="evidence"),
        Detection(risk_class=RiskClass.TOXICITY, score=0.7, source=Source.TEXT, filter="AlwaysDetectFilter", detail="evidence"),
    )
    state.set(
        "PermanentFailFilter",
        FilterOutcome(content_id="c-1", status=FilterStatus.COMPLETED, detections=[]),
    )
    item = make_item("c-1")
    decision = ResultAggregator().aggregate(item, state, [AlwaysDetectFilter, PermanentFailFilter], processing_ms=42)

    assert decision.status == DecisionStatus.COMPLETE
    assert decision.processing_ms == 42
    assert len(decision.detections) == 1
    aggregate = decision.detections[0]
    assert aggregate.risk_class == RiskClass.TOXICITY
    assert aggregate.score == 0.9  # max
    assert [d.score for d in aggregate.evidence] == [0.9, 0.7]
    assert aggregate.sources == [Source.TEXT]
    report_names = {f.filter for f in decision.filters_report}
    assert report_names == {"AlwaysDetectFilter", "PermanentFailFilter"}
    all_completed = all(f.status == FilterStatus.COMPLETED for f in decision.filters_report)
    assert all_completed


@pytest.mark.unit
def test_aggregate_sources_sorted_and_dedup_classes() -> None:
    state = BatchState.new(
        make_payload(active_classes=[RiskClass.TOXICITY]),
        max_retries=3,
    )
    state.ensure_filter("AlwaysDetectFilter", ["c-1"])
    state.ensure_filter("PermanentFailFilter", ["c-1"])
    _add_multi(
        state,
        "AlwaysDetectFilter",
        "c-1",
        Detection(risk_class=RiskClass.TOXICITY, score=0.5, source=Source.TEXT, filter="AlwaysDetectFilter", detail="evidence"),
        Detection(risk_class=RiskClass.TOXICITY, score=0.6, source=Source.BEHAVIOR, filter="AlwaysDetectFilter", detail="evidence"),
    )
    state.set(
        "PermanentFailFilter",
        FilterOutcome(content_id="c-1", status=FilterStatus.COMPLETED, detections=[]),
    )
    decision = ResultAggregator().aggregate(make_item("c-1"), state, [AlwaysDetectFilter, PermanentFailFilter])
    assert len(decision.detections) == 1
    aggregate = decision.detections[0]
    assert aggregate.score == 0.6
    assert aggregate.sources == [Source.BEHAVIOR, Source.TEXT]  # tri par valeur


@pytest.mark.unit
def test_aggregate_partial_when_filter_failed() -> None:
    state = _state_with()
    _add_txt(state, "AlwaysDetectFilter", "c-1", 0.9, Source.TEXT)
    state.mark_failed(
        "PermanentFailFilter",
        "c-1",
        PermanentFilterError("nope", filter_name="PermanentFailFilter", content_ids=["c-1"]),
    )
    decision = ResultAggregator().aggregate(make_item("c-1"), state, [AlwaysDetectFilter, PermanentFailFilter])
    assert decision.status == DecisionStatus.PARTIAL
    records = {f.filter: f for f in decision.filters_report}
    assert records["AlwaysDetectFilter"].status == FilterStatus.COMPLETED
    assert records["PermanentFailFilter"].status == FilterStatus.FAILED
    assert records["PermanentFailFilter"].attempts == 1
    assert records["PermanentFailFilter"].error is not None


@pytest.mark.unit
def test_aggregate_skipped_filters_reported() -> None:
    state = BatchState.new(
        make_payload(active_classes=[RiskClass.TOXICITY]),
        max_retries=3,
    )
    state.ensure_filter("AlwaysDetectFilter", ["c-1"])
    state.ensure_filter("PermanentFailFilter", ["c-1"])
    state.set("PermanentFailFilter", FilterOutcome(content_id="c-1", status=FilterStatus.SKIPPED))
    _add_txt(state, "AlwaysDetectFilter", "c-1", 0.9, Source.TEXT)
    decision = ResultAggregator().aggregate(make_item("c-1"), state, [AlwaysDetectFilter, PermanentFailFilter])
    report = {f.filter: f.status for f in decision.filters_report}
    assert report == {"AlwaysDetectFilter": FilterStatus.COMPLETED, "PermanentFailFilter": FilterStatus.SKIPPED}
    assert decision.status == DecisionStatus.COMPLETE


@pytest.mark.unit
def test_aggregate_filters_detections_outside_active_classes() -> None:
    state = BatchState.new(make_payload(active_classes=[RiskClass.TOXICITY]), max_retries=3)
    state.ensure_filter("AlwaysDetectFilter", ["c-1"])
    state.set(
        "AlwaysDetectFilter",
        FilterOutcome(
            content_id="c-1",
            status=FilterStatus.COMPLETED,
            detections=[
                Detection(risk_class=RiskClass.SEXUAL, score=0.9, source=Source.TEXT, filter="AlwaysDetectFilter"),
            ],
        ),
    )
    decision = ResultAggregator().aggregate(make_item("c-1"), state, [AlwaysDetectFilter])
    assert decision.detections == []  # SEXUAL filtré hors activeClasses
