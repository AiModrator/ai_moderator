"""`ImageAIFilter` — détection IA sur images (batch, AI Gateway, main.md §5.5)."""

from __future__ import annotations

import asyncio

import structlog

from app.clients.ai_gateway import AIGatewayClient
from app.errors import PermanentFilterError, TransientFilterError
from app.filters._ai_common import translate_gateway_error
from app.filters.base import BatchFilter
from app.filters.registry import register_filter
from app.schemas.ai_gateway import ModerationResponse
from app.schemas.enums import AttachmentType, FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.result import Detection, FilterContext, FilterOutcome

IMAGE_AI_CLASSES = frozenset(
    {
        RiskClass.HATE_SPEECH,
        RiskClass.SEXUAL,
        RiskClass.VIOLENCE,
        RiskClass.ILLEGAL,
        RiskClass.SELF_HARM,
    }
)


@register_filter
class ImageAIFilter(BatchFilter):
    """Un appel par image et par classe (plafond `MAX_IMAGES_PER_ITEM`, §5.5).

    - Applicable s'il y a au moins un attachment `image` ; `video` ignoré et noté
      (`"video unsupported"`) ; images au-delà du plafond ignorées (`detail`).
    - L'URL de l'image est transmise telle quelle (pas de téléchargement en v1).
    - Agrégation intra-item : `max score` par classe ; `detail="image#N: reason"`.
    - Erreur transitoire sur une image → item `PENDING_RETRY` (toutes ses images
      sont ré-évaluées au retry) ; erreur permanente → item `FAILED`.
    """

    NAME = "ImageAIFilter"
    HANDLED_CLASSES = IMAGE_AI_CLASSES

    def __init__(
        self,
        client: AIGatewayClient,
        *,
        max_images_per_item: int = 4,
        timeout_sec: float = 10.0,
    ) -> None:
        self._client = client
        self.max_images_per_item = max_images_per_item
        self.TIMEOUT_SEC = timeout_sec
        self._logger = structlog.get_logger()

    def is_applicable(self, item: ContentItem) -> bool:
        return any(attachment.type == AttachmentType.IMAGE for attachment in item.attachments)

    async def evaluate_batch(self, items: list[ContentItem], ctx: FilterContext) -> list[FilterOutcome]:
        outcomes: dict[str, FilterOutcome] = {}
        applicable: list[ContentItem] = []
        for item in items:
            if self.is_applicable(item):
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

        image_calls: list[tuple[RiskClass, list[ContentItem], int, str]] = []
        for item in applicable:
            images = [
                attachment
                for attachment in item.attachments
                if attachment.type == AttachmentType.IMAGE
            ]
            for risk_class in classes:
                for index, image in enumerate(images[: self.max_images_per_item]):
                    image_calls.append((risk_class, item, index + 1, str(image.url)))

        results = await asyncio.gather(
            *(self._call(risk_class, image_index, url) for risk_class, _item, image_index, url in image_calls),
            return_exceptions=True,
        )

        transitory_ids: set[str] = set()
        permanent_ids: set[str] = set()
        detections_by_item: dict[str, dict[RiskClass, Detection]] = {}
        for (risk_class, item, image_index, url), call_result in zip(image_calls, results, strict=True):
            if isinstance(call_result, Exception):
                translated = translate_gateway_error(call_result, self.NAME, self._logger)
                if isinstance(translated, PermanentFilterError):
                    permanent_ids.add(item.content_id)
                else:
                    transitory_ids.add(item.content_id)
                continue
            response = call_result[3]
            self._collect_ok(item, risk_class, image_index, url, response, detections_by_item)

        affected_trans = transitory_ids - permanent_ids
        self._complete(applicable, outcomes, detections_by_item, affected_trans | permanent_ids)

        if permanent_ids:
            raise PermanentFilterError(
                "ImageAIFilter permanent failure",
                filter_name=self.NAME,
                content_ids=sorted(permanent_ids),
                partial_outcomes=self._ordered(items, outcomes),
            )
        if affected_trans:
            raise TransientFilterError(
                "ImageAIFilter transient failure",
                filter_name=self.NAME,
                content_ids=sorted(affected_trans),
                partial_outcomes=self._ordered(items, outcomes),
            )
        return self._ordered(items, outcomes)

    async def _call(self, risk_class: RiskClass, image_index: int, url: str) -> tuple[RiskClass, int, str, ModerationResponse]:
        response = await self._client.moderate(risk_class.value, "image", [(url, url)])
        return risk_class, image_index, url, response

    def _collect_ok(
        self,
        item: ContentItem,
        risk_class: RiskClass,
        image_index: int,
        url: str,
        response: ModerationResponse,
        detections_by_item: dict[str, dict[RiskClass, Detection]],
    ) -> None:
        by_id = {result.id: result for result in response.results}
        result = by_id.get(url)
        # résultat absent pour cette image → score 0 (contrat phase-04 §2.1)
        if result is None or result.score <= 0:
            return
        per_item = detections_by_item.setdefault(item.content_id, {})
        current = per_item.get(risk_class)
        if current is None or result.score > current.score:
            detail = f"image#{image_index}: {result.reason}" if result.reason else f"image#{image_index}"
            notes = self._notes(item)
            if notes:
                detail = f"{detail}; {'; '.join(notes)}"
            per_item[risk_class] = Detection(
                risk_class=risk_class,
                score=min(result.score, 1.0),
                source=Source.IMAGE,
                filter=self.NAME,
                detail=detail,
            )

    def _notes(self, item: ContentItem) -> list[str]:
        notes: list[str] = []
        if any(attachment.type == AttachmentType.VIDEO for attachment in item.attachments):
            notes.append("video unsupported")
        image_count = sum(1 for a in item.attachments if a.type == AttachmentType.IMAGE)
        if image_count > self.max_images_per_item:
            notes.append(f"{image_count - self.max_images_per_item} image(s) ignored")
        return notes

    def _complete(
        self,
        applicable: list[ContentItem],
        outcomes: dict[str, FilterOutcome],
        detections_by_item: dict[str, dict[RiskClass, Detection]] | None = None,
        excluded_ids: set[str] | None = None,
    ) -> None:
        detections_by_item = detections_by_item or {}
        excluded_ids = excluded_ids or set()
        for item in applicable:
            if item.content_id in excluded_ids:
                continue
            full_class_detections = [
                detections_by_item.get(item.content_id, {}).get(risk_class)
                for risk_class in sorted(detections_by_item.get(item.content_id, {}), key=str)
            ]
            detections = [detection for detection in full_class_detections if detection is not None]
            outcomes[item.content_id] = FilterOutcome(
                content_id=item.content_id,
                status=FilterStatus.COMPLETED,
                detections=detections,
            )

    @staticmethod
    def _ordered(items: list[ContentItem], outcomes: dict[str, FilterOutcome]) -> list[FilterOutcome]:
        return [outcomes[item.content_id] for item in items if item.content_id in outcomes]


__all__ = ["ImageAIFilter", "IMAGE_AI_CLASSES"]
