"""Fixtures de données : `ContentItem`, `ContentBatchJob`, `FilterContext`."""

from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.enums import ContentType, RiskClass
from app.schemas.job import ContentBatchJob, ContentItem
from app.schemas.result import FilterContext


def make_item(
    content_id: str = "c-1",
    text: str = "hello world",
    content_type: ContentType = ContentType.COMMENT,
    user_ref: str = "u-1",
    attachments: list | None = None,
) -> ContentItem:
    return ContentItem(
        content_id=content_id,
        content_type=content_type,
        user_ref=user_ref,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        text=text,
        attachments=attachments or [],
    )


def make_payload(
    items: list[ContentItem] | None = None,
    active_classes: list[RiskClass] | None = None,
    batch_id: str = "batch-1",
    community_ref: str = "community-A",
) -> ContentBatchJob:
    return ContentBatchJob(
        batch_id=batch_id,
        community_ref=community_ref,
        active_classes=active_classes or [RiskClass.TOXICITY],
        items=items or [make_item()],
    )


def make_context(target_classes: set[RiskClass] | None = None) -> FilterContext:
    return FilterContext(
        batch_id="batch-1",
        community_ref="community-A",
        attempt=0,
        target_classes=target_classes or {RiskClass.TOXICITY},
    )


__all__ = ["make_item", "make_payload", "make_context"]
