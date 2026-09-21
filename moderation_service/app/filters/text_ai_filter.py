"""`TextAIFilter` — détection IA sur texte (batch, AI Gateway, main.md §5.4)."""

from __future__ import annotations

import asyncio

import structlog

from app.clients.ai_gateway import AIGatewayClient
from app.core.text_normalizer import normalize
from app.errors import PermanentFilterError, TransientFilterError
from app.filters._ai_common import translate_gateway_error, truncate_content
from app.filters.base import BatchFilter
from app.filters.registry import register_filter
from app.schemas.ai_gateway import ModerationResponse
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.result import Detection, FilterContext, FilterOutcome

TEXT_AI_CLASSES = frozenset(
    {
        RiskClass.SCAM,
        RiskClass.PHISHING,
        RiskClass.ADVERTISING,
        RiskClass.TOXICITY,
        RiskClass.INSULT,
        RiskClass.HARASSMENT,
        RiskClass.THREAT,
        RiskClass.HATE_SPEECH,
        RiskClass.SEXUAL,
        RiskClass.VIOLENCE,
        RiskClass.ILLEGAL,
        RiskClass.SELF_HARM,
    }
)


@register_filter
class TextAIFilter(BatchFilter):
    """Un appel par classe cible et par sous-lot (`AI_TEXT_BATCH_SIZE`, §5.4).

    - Items non applicables (`< AI_TEXT_MIN_CHARS` après normalisation) → `SKIPPED`.
    - Texte tronqué à `AI_TEXT_MAX_CHARS_PER_ITEM` (+ suffixe `…[tronqué]`).
    - Sous-lots et classes exécutés en parallèle, plafonnés par le sémaphore du
      client (`AI_MAX_PARALLEL_REQUESTS`).
    - `id` inconnu → ignoré (warn) ; `score == 0` → pas de détection ; item absent
      de `results` → `PENDING_RETRY` pour lui seul (via `TransientFilterError`).
    """

    NAME = "TextAIFilter"
    HANDLED_CLASSES = TEXT_AI_CLASSES

    def __init__(
        self,
        client: AIGatewayClient,
        *,
        min_chars: int = 2,
        batch_size: int = 10,
        max_chars_per_item: int = 4000,
        timeout_sec: float = 10.0,
    ) -> None:
        self._client = client
        self.min_chars = min_chars
        self.batch_size = batch_size
        self.max_chars_per_item = max_chars_per_item
        self.TIMEOUT_SEC = timeout_sec
        self._logger = structlog.get_logger()

    def is_applicable(self, item: ContentItem) -> bool:
        if item.text is None:
            return False
        return len(normalize(item.text).raw) >= self.min_chars

    async def evaluate_batch(self, items: list[ContentItem], ctx: FilterContext) -> list[FilterOutcome]:
        outcomes: dict[str, FilterOutcome] = {}
        applicable: list[ContentItem] = []
        for item in items:
            if item.text is not None and self.is_applicable(item):
                applicable.append(item)
            else:
                outcomes[item.content_id] = FilterOutcome(
                    content_id=item.content_id, status=FilterStatus.SKIPPED
                )

        classes = sorted(ctx.target_classes & self.HANDLED_CLASSES, key=str)
        if not applicable:
            return self._ordered(items, outcomes)
        if not classes:
            for item in applicable:
                outcomes[item.content_id] = FilterOutcome(
                    content_id=item.content_id, status=FilterStatus.SKIPPED
                )
            return self._ordered(items, outcomes)

        calls: list[tuple[RiskClass, list[ContentItem]]] = []
        for risk_class in classes:
            for start in range(0, len(applicable), self.batch_size):
                calls.append((risk_class, list(applicable[start : start + self.batch_size])))

        results = await asyncio.gather(
            *(self._call(risk_class, sub) for risk_class, sub in calls),
            return_exceptions=True,
        )

        detections_by_item: dict[str, list[Detection]] = {}
        transitory_ids: set[str] = set()
        permanent_ids: set[str] = set()
        missing_ids: set[str] = set()

        for (risk_class, sub), result in zip(calls, results, strict=True):
            if isinstance(result, Exception):
                translated = translate_gateway_error(result, self.NAME, self._logger)
                sub_ids = {item.content_id for item in sub}
                if isinstance(translated, PermanentFilterError):
                    permanent_ids |= sub_ids
                else:
                    transitory_ids |= sub_ids
                continue
            self._collect_ok(risk_class, sub, result, detections_by_item, missing_ids, transitory_ids)

        affected_trans = (transitory_ids | missing_ids) - permanent_ids
        completed_ids = {item.content_id for item in applicable} - affected_trans - permanent_ids
        self._complete(applicable, outcomes, completed_ids, detections_by_item)

        if permanent_ids:
            raise PermanentFilterError(
                "TextAIFilter permanent failure",
                filter_name=self.NAME,
                content_ids=sorted(permanent_ids),
                partial_outcomes=self._ordered(items, outcomes),
            )
        if affected_trans:
            raise TransientFilterError(
                "TextAIFilter transient failure",
                filter_name=self.NAME,
                content_ids=sorted(affected_trans),
                partial_outcomes=self._ordered(items, outcomes),
            )
        return self._ordered(items, outcomes)

    async def _call(self, risk_class: RiskClass, sub: list[ContentItem]) -> ModerationResponse:
        return await self._client.moderate(
            risk_class.value,
            "text",
            [(item.content_id, truncate_content(item.text or "", self.max_chars_per_item)) for item in sub],
        )

    def _collect_ok(
        self,
        risk_class: RiskClass,
        sub: list[ContentItem],
        response: ModerationResponse,
        detections_by_item: dict[str, list[Detection]],
        missing_ids: set[str],
        transitory_ids: set[str],
    ) -> None:
        sub_ids = {item.content_id for item in sub}
        by_id = {result.id: result for result in response.results}
        unknown = set(by_id) - sub_ids
        if unknown:
            self._logger.warning("ai.unknown_result_id", filter="TextAIFilter", ids=sorted(unknown))
        for item in sub:
            if item.content_id not in by_id:
                missing_ids.add(item.content_id)
                continue
            result = by_id[item.content_id]
            if result.score <= 0:
                continue
            detections_by_item.setdefault(item.content_id, []).append(
                Detection(
                    risk_class=risk_class,
                    score=min(result.score, 1.0),
                    source=Source.TEXT,
                    filter=self.NAME,
                    detail=result.reason,
                )
            )

    def _complete(
        self,
        applicable: list[ContentItem],
        outcomes: dict[str, FilterOutcome],
        completed_ids: set[str] | None = None,
        detections_by_item: dict[str, list[Detection]] | None = None,
    ) -> None:
        detections_by_item = detections_by_item or {}
        for item in applicable:
            if completed_ids is not None and item.content_id not in completed_ids:
                continue
            detections = sorted(detections_by_item.get(item.content_id, []), key=str)
            outcomes[item.content_id] = FilterOutcome(
                content_id=item.content_id,
                status=FilterStatus.COMPLETED,
                detections=detections,
            )

    @staticmethod
    def _ordered(items: list[ContentItem], outcomes: dict[str, FilterOutcome]) -> list[FilterOutcome]:
        return [outcomes[item.content_id] for item in items if item.content_id in outcomes]


__all__ = ["TextAIFilter", "TEXT_AI_CLASSES"]
