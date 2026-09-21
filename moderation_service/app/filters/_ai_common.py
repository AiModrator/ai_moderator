"""Partage entre `TextAIFilter` et `ImageAIFilter` : traduction d'erreurs et troncature."""

from __future__ import annotations

import structlog

from app.core.text_normalizer import normalize
from app.errors import (
    AIGatewayBadRequestError,
    AIGatewayBudgetExceededError,
    FilterError,
    PermanentFilterError,
    TransientFilterError,
)

TRUNCATED_SUFFIX = "…[tronqué]"


def truncate_content(text: str, max_chars: int) -> str:
    """Contenu envoyé à la gateway : texte normalisé, tronqué avec suffixe prévisible."""
    content = normalize(text).raw
    if len(content) > max_chars:
        return content[:max_chars] + TRUNCATED_SUFFIX
    return content


def translate_gateway_error(exc: Exception, filter_name: str, logger: structlog.stdlib.BoundLogger) -> FilterError:
    """Traduit une `AIGatewayError` en `TransientFilterError`/`PermanentFilterError` (§7)."""
    if isinstance(exc, AIGatewayBudgetExceededError):
        logger.error("ai.budget_exceeded", filter_name=filter_name)
        return TransientFilterError(str(exc), filter_name=filter_name)
    if isinstance(exc, AIGatewayBadRequestError):
        return PermanentFilterError(str(exc), filter_name=filter_name)
    return TransientFilterError(str(exc), filter_name=filter_name)


__all__ = ["truncate_content", "translate_gateway_error", "TRUNCATED_SUFFIX"]
