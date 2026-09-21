"""`LexiconFilter` — détection déterministe par lexique (main.md §5.3)."""

from __future__ import annotations

from app.core.text_normalizer import normalize
from app.filters.base import ItemFilter
from app.filters.lexicon_repository import LexiconRepository
from app.filters.registry import register_filter
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.result import Detection, FilterContext, FilterOutcome

_BONUS_PER_EXTRA_PATTERN = 0.05
_BONUS_CAP = 0.15


@register_filter
class LexiconFilter(ItemFilter):
    """Détection par lexique (classes §4.2), matching `lower` + `deobfuscated`.

    Score par classe : `base = max(pattern.score)` des patterns matchés,
    +0.05 par pattern distinct supplémentaire (plafonné à `base + 0.15`, puis
    à 1.0), le tout **borné par `max_score`** (`LEXICON_MAX_SCORE`, défaut 0.85) :
    un lexique seul ne produit jamais un score maximal — filet de sécurité
    quand `TextAIFilter` est `UNAVAILABLE`.
    """

    NAME = "LexiconFilter"
    HANDLED_CLASSES = frozenset(
        {
            RiskClass.INSULT,
            RiskClass.HATE_SPEECH,
            RiskClass.SEXUAL,
            RiskClass.THREAT,
            RiskClass.VIOLENCE,
            RiskClass.SELF_HARM,
            RiskClass.ILLEGAL,
            RiskClass.ADVERTISING,
            RiskClass.SCAM,
        }
    )

    def __init__(self, repository: LexiconRepository, *, max_score: float = 0.85, timeout_sec: float = 10.0) -> None:
        self._repository = repository
        self.max_score = max_score
        self.TIMEOUT_SEC = timeout_sec

    def is_applicable(self, item: ContentItem) -> bool:
        if item.text is None:
            return False
        return bool(normalize(item.text).raw)

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        content_id = item.content_id
        if item.text is None:
            return FilterOutcome(content_id=content_id, status=FilterStatus.SKIPPED)

        normalized = normalize(item.text)
        if not normalized.raw:
            return FilterOutcome(content_id=content_id, status=FilterStatus.SKIPPED)

        detections: list[Detection] = []
        targets = sorted(ctx.target_classes & self.HANDLED_CLASSES, key=str)
        for risk_class in targets:
            matched = [
                pattern
                for pattern in self._repository.patterns_for(risk_class)
                if pattern.regex.search(normalized.lower) or pattern.regex.search(normalized.deobfuscated)
            ]
            if not matched:
                continue
            matched_desc = sorted(matched, key=lambda p: p.score, reverse=True)
            base = matched_desc[0].score
            bonus = min(len(matched_desc) - 1, _BONUS_CAP / _BONUS_PER_EXTRA_PATTERN) * _BONUS_PER_EXTRA_PATTERN
            score = min(base + bonus, 1.0)
            score = min(score, self.max_score)
            names = ", ".join(p.pattern for p in matched_desc)
            detections.append(
                Detection(
                    risk_class=risk_class,
                    score=score,
                    source=Source.TEXT,
                    filter=self.NAME,
                    detail=f"match: {names}",
                )
            )
        return FilterOutcome(content_id=content_id, status=FilterStatus.COMPLETED, detections=detections)


__all__ = ["LexiconFilter"]
