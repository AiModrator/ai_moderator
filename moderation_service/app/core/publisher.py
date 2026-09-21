"""Publication `decisionQueue` et republication retry `contentQueue` — main.md §3.4 / §6.4."""

from __future__ import annotations

from bullmq import Queue

from app.config.settings import Settings
from app.errors import PublishError
from app.schemas.decision import DecisionJob
from app.schemas.job import ContentBatchJob
from app.schemas.state import RetryState

DECISION_JOB_NAME = "decide"
MODERATE_JOB_NAME = "moderateBatch"

# Options de la décision (§3.4) : retry BullMQ = ressort de l'Action Service.
_DECISION_OPTS = {
    "attempts": 5,
    "backoff": {"type": "exponential", "delay": 2000},
    "removeOnComplete": True,
}


def build_queue(name: str, settings: Settings) -> Queue:
    """Queue BullMQ attachée au Redis du service, préfixée par `test_queue_prefix` en test."""
    connection = {
        "host": settings.redis_host,
        "port": settings.redis_port,
        "password": settings.redis_password or None,
    }
    prefix = settings.test_queue_prefix or "bull"
    return Queue(name, {"connection": connection, "prefix": prefix})


class DecisionPublisher:
    """Publie `DecisionJob` vers la `decisionQueue` (un job par contenu)."""

    def __init__(self, queue: Queue) -> None:
        self._queue = queue

    async def publish(self, decision: DecisionJob) -> None:
        """Job `decide`, `jobId = "{batchId}:{contentId}"` → publication idempotente."""
        data = decision.model_dump(mode="json", by_alias=True)
        job_id = f"{decision.batch_id}:{decision.content.content_id}"
        try:
            await self._queue.add(DECISION_JOB_NAME, data, {**{"jobId": job_id}, **_DECISION_OPTS})
        except Exception as exc:  # infra BullMQ/Redis → remonte à BullMQ (job failed)
            raise PublishError(f"decision publication failed: {exc}") from exc


def restrict_payload(payload: ContentBatchJob, unresolved: list[str], retry_state: RetryState) -> dict:
    """Payload de retry §6.4 : items non résolus uniquement + `retryState`."""
    unresolved_set = set(unresolved)
    data = payload.model_dump(mode="json", by_alias=True)
    data["items"] = [
        item for item in data["items"] if item["contentId"] in unresolved_set
    ]
    data["retryState"] = retry_state.model_dump(mode="json", by_alias=True)
    return data


class RetryScheduler:
    """Republie un lot non terminé dans `contentQueue` avec `delay` + `retryState` (§6.4)."""

    def __init__(self, queue: Queue, *, base_delay_ms: int, max_delay_ms: int) -> None:
        self._queue = queue
        self._base_delay_ms = base_delay_ms
        self._max_delay_ms = max_delay_ms

    def delay_for(self, attempt: int) -> int:
        """Backoff exponentiel : `min(BASE * 2 ** attempt, MAX)`, attempt 0 → base."""
        return min(int(self._base_delay_ms * (2 ** max(attempt, 0))), self._max_delay_ms)

    async def schedule(self, payload: ContentBatchJob, retry_state: RetryState, unresolved: list[str]) -> None:
        """Paylod restreint aux items non résolus + `retryState` ; `jobId="{batchId}:retry:{next}"`."""
        next_attempt = retry_state.attempt
        data = restrict_payload(payload, unresolved, retry_state)
        job_id = f"{payload.batch_id}:retry:{next_attempt}"
        try:
            await self._queue.add(
                MODERATE_JOB_NAME,
                data,
                {
                    "delay": self.delay_for(next_attempt - 1),
                    "attempts": 1,
                    "jobId": job_id,
                },
            )
        except Exception as exc:  # infra
            raise PublishError(f"retry publication failed: {exc}") from exc


__all__ = ["DecisionPublisher", "RetryScheduler", "build_queue", "restrict_payload"]
