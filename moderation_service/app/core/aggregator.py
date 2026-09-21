"""Agrégation des détections en `DecisionJob` — `ResultAggregator` (main.md §8)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.decision import (
    AggregatedDetection,
    ContentRef,
    DecisionJob,
    DecisionStatus,
    FilterReport,
)
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.state import BatchState


class ResultAggregator:
    """Transforme (item, état du lot, pipeline) en job `decisionQueue`."""

    def aggregate(
        self,
        item: ContentItem,
        state: BatchState,
        pipeline: list,
        processing_ms: int = 0,
    ) -> DecisionJob:
        """Agrège selon §8 : max score par classe, sources triées, evidence triée."""
        by_class: dict[RiskClass, list] = {}
        for filter_cls in pipeline:
            fstate = state.filters[filter_cls.NAME]
            istate = fstate.items[item.content_id]
            if istate.status != FilterStatus.COMPLETED:
                continue
            for detection in istate.detections:
                if detection.risk_class in state.active_classes:
                    by_class.setdefault(detection.risk_class, []).append(detection)

        detections: list[AggregatedDetection] = []
        for risk_class, dets in by_class.items():
            winner = max(dets, key=lambda d: d.score)
            sources = sorted({d.source.value for d in dets})
            evidence = sorted(dets, key=lambda d: d.score, reverse=True)
            detections.append(
                AggregatedDetection(
                    risk_class=risk_class,
                    score=winner.score,
                    sources=[Source(s) for s in sources],
                    evidence=evidence,
                )
            )
        detections.sort(key=lambda ag: ag.score, reverse=True)

        report: list[FilterReport] = []
        complete = True
        for filter_cls in pipeline:
            istate = state.filters[filter_cls.NAME].items[item.content_id]
            report.append(
                FilterReport(
                    filter=filter_cls.NAME,
                    status=istate.status,
                    attempts=istate.attempts,
                    error=istate.last_error,
                )
            )
            if istate.status not in (FilterStatus.COMPLETED, FilterStatus.SKIPPED):
                complete = False

        return DecisionJob(
            batch_id=state.batch_id,
            community_ref=state.community_ref,
            content=ContentRef(
                content_id=item.content_id,
                content_type=item.content_type,
                user_ref=item.user_ref,
                timestamp=item.timestamp,
            ),
            active_classes=list(state.active_classes),
            status=DecisionStatus.COMPLETE if complete else DecisionStatus.PARTIAL,
            detections=detections,
            filters_report=report,
            moderated_at=datetime.now(UTC),
            processing_ms=processing_ms,
        )


__all__ = ["ResultAggregator"]
