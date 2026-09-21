"""`SpamFilter` — détection comportementale de spam adossée à Redis (main.md §5.1)."""

from __future__ import annotations

import hashlib

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.text_normalizer import normalize
from app.errors import TransientFilterError
from app.filters._spam_heuristics import compute_heuristics
from app.filters.base import ItemFilter
from app.filters.registry import register_filter
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.result import Detection, FilterContext, FilterOutcome

_DUP_KEY_PREFIX = "mod:spam:dup"
_FLOOD_KEY_PREFIX = "mod:spam:flood"


def dup_score(count: int) -> float:
    """Sous-score doublon : tableau §5.1."""
    if count >= 10:
        return 0.95
    if count >= 5:
        return 0.80
    if count >= 3:
        return 0.60
    if count == 2:
        return 0.40
    return 0.0


def flood_score(count: int, threshold: int) -> float:
    """Sous-score flood : tableau §5.1 (multiples du seuil)."""
    if count <= threshold:
        return 0.0
    if count <= 2 * threshold:
        return 0.60
    if count <= 4 * threshold:
        return 0.80
    return 0.95


def heuristic_score(num_triggered: int) -> float:
    """Sous-score heuristiques : 0 / 1 / 2 / ≥3 → 0 / 0.30 / 0.50 / 0.70."""
    if num_triggered >= 3:
        return 0.70
    if num_triggered == 2:
        return 0.50
    if num_triggered == 1:
        return 0.30
    return 0.0


@register_filter
class SpamFilter(ItemFilter):
    """Filtre de spam (item) : doublon + flood (Redis) + heuristiques textuelles.

    Applicable toujours ; si ni texte ni attachment → outcome `SKIPPED`.
    Une erreur Redis (réseau/timeout) → `TransientFilterError` : aucun compteur
    n'est incrémenté (transaction MULTI/EXEC all-or-nothing).
    """

    NAME = "SpamFilter"
    HANDLED_CLASSES = frozenset({RiskClass.SPAM})

    def __init__(
        self,
        redis: Redis,
        *,
        dup_window_sec: int = 3600,
        flood_window_sec: int = 60,
        flood_threshold: int = 10,
        timeout_sec: float = 10.0,
    ) -> None:
        self._redis = redis
        self.dup_window_sec = dup_window_sec
        self.flood_window_sec = flood_window_sec
        self.flood_threshold = flood_threshold
        self.TIMEOUT_SEC = timeout_sec

    def is_applicable(self, item: ContentItem) -> bool:
        return True

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        content_id = item.content_id
        text = item.text
        attachments = item.attachments

        if (not text or not text.strip()) and not attachments:
            return FilterOutcome(content_id=content_id, status=FilterStatus.SKIPPED)

        normalized = normalize(text) if text else None
        if normalized is not None and normalized.raw:
            dup_source = normalized.deobfuscated
        else:
            dup_source = "|".join(sorted(str(a.url) for a in attachments))

        if not dup_source:
            return FilterOutcome(content_id=content_id, status=FilterStatus.SKIPPED)

        dup_key = f"{_DUP_KEY_PREFIX}:{ctx.community_ref}:{self._sha256(dup_source)}"
        flood_key = f"{_FLOOD_KEY_PREFIX}:{ctx.community_ref}:{item.user_ref}"

        try:
            dup_count, flood_count = await self._counters(dup_key, flood_key)
        except (TimeoutError, RedisError, OSError) as exc:
            raise TransientFilterError(
                str(exc), filter_name=self.NAME, content_ids=[content_id]
            ) from exc

        triggers = (
            compute_heuristics(raw=normalized.raw, urls=normalized.urls, tokens=normalized.tokens)
            if normalized and normalized.raw
            else []
        )

        score = max(
            dup_score(dup_count),
            flood_score(flood_count, self.flood_threshold),
            heuristic_score(len(triggers)),
        )
        if score <= 0:
            return FilterOutcome(content_id=content_id, status=FilterStatus.COMPLETED)

        detail = f"dup={dup_count},flood={flood_count},heur=[{','.join(triggers)}]"
        detection = Detection(
            risk_class=RiskClass.SPAM,
            score=score,
            source=Source.BEHAVIOR,
            filter=self.NAME,
            detail=detail,
        )
        return FilterOutcome(
            content_id=content_id,
            status=FilterStatus.COMPLETED,
            detections=[detection],
        )

    async def _counters(self, dup_key: str, flood_key: str) -> tuple[int, int]:
        """INCR (doublon + flood) dans une même transaction → soit tout, soit rien."""
        pipe = self._redis.pipeline(transaction=True)
        pipe.incr(dup_key)
        pipe.incr(flood_key)
        dup_count, flood_count = await pipe.execute()
        if dup_count == 1:
            await self._redis.expire(dup_key, self.dup_window_sec)
        if flood_count == 1:
            await self._redis.expire(flood_key, self.flood_window_sec)
        return int(dup_count), int(flood_count)

    @staticmethod
    def _sha256(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = ["SpamFilter", "dup_score", "flood_score", "heuristic_score"]
