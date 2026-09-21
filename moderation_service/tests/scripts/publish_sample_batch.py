"""Publie un `ContentBatchJob` d'exemple dans `contentQueue` (test manuel bout en bout).

Usage (depuis `moderation_service/`, venv activé) :

    python -m tests.scripts.publish_sample_batch [--batch-id ID]
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from app.config.logging import configure_logging, get_logger
from app.config.settings import Settings
from app.core.publisher import MODERATE_JOB_NAME, build_queue
from app.schemas.enums import ContentType, RiskClass
from app.schemas.job import ContentBatchJob, ContentItem


def _item(content_id: str, text: str) -> ContentItem:
    return ContentItem(
        content_id=content_id,
        content_type=ContentType.COMMENT,
        user_ref=f"user-{content_id}",
        timestamp=datetime.now(UTC),
        text=text,
    )


def build_sample(batch_id: str) -> ContentBatchJob:
    """Lot d'exemple : 2 items, classes `SPAM` + `TOXICITY`."""
    return ContentBatchJob(
        batch_id=batch_id,
        community_ref="sample-community",
        active_classes=[RiskClass.SPAM, RiskClass.TOXICITY],
        items=[
            _item("sample-1", "Buy cheap followers now !!! visit my spam link"),
            _item("sample-2", "I hate you all, you are worthless"),
        ],
    )


async def publish(batch_id: str) -> None:
    settings = Settings()
    configure_logging(settings)
    log = get_logger()
    queue = build_queue(settings.content_queue_name, settings)
    payload = build_sample(batch_id)
    await queue.add(
        MODERATE_JOB_NAME,
        payload.model_dump(mode="json", by_alias=True),
        {"jobId": batch_id},
    )
    log.info(
        "sample.published",
        jobId=batch_id,
        items=len(payload.items),
        queue=settings.content_queue_name,
    )
    await queue.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Publie un lot d'exemple dans contentQueue")
    parser.add_argument("--batch-id", default="sample-batch", help="jobId du lot (défaut : sample-batch)")
    args = parser.parse_args()
    asyncio.run(publish(args.batch_id))


if __name__ == "__main__":
    main()
