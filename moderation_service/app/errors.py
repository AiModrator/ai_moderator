"""Hiérarchie d'erreurs du service (main.md §7).

Règle : le `Worker` ne connaît que `FilterError` et ses sous-classes.
`AIGatewayClient` lève des `AIGatewayError` ; les filtres IA les traduisent.
"""

from __future__ import annotations

from typing import ClassVar

from app.schemas.result import FilterOutcome


class ModerationError(Exception):
    """Racine de toutes les erreurs du service."""


class InvalidJobPayloadError(ModerationError):
    """Payload `contentQueue` invalide → job `failed`, pas de retry BullMQ."""


class PublishError(ModerationError):
    """Échec d'infrastructure lors de la publication vers une queue."""


class FilterError(ModerationError):
    """Une erreur survenue dans un filtre (gérée par le Worker)."""

    filter_name: str
    content_ids: list[str] | None  # None = tous les items passés au filtre
    partial_outcomes: list[FilterOutcome]
    retryable: ClassVar[bool] = False

    def __init__(
        self,
        message: str = "",
        *,
        filter_name: str = "",
        content_ids: list[str] | None = None,
        partial_outcomes: list[FilterOutcome] | None = None,
    ) -> None:
        super().__init__(message or self.__class__.__name__)
        self.filter_name = filter_name
        self.content_ids = content_ids
        self.partial_outcomes = partial_outcomes or []

    def __str__(self) -> str:
        base = super().__str__()
        if self.content_ids:
            return f"{base} [{','.join(self.content_ids)}]"
        return base


class TransientFilterError(FilterError):
    """Erreur transitoire (réseau, timeout, 429/5xx, Redis KO) → retry."""

    retryable: ClassVar[bool] = True


class FilterTimeoutError(TransientFilterError):
    """Timeout appliqué par le Worker (`asyncio.wait_for`)."""


class PermanentFilterError(FilterError):
    """Erreur permanente (4xx, config invalide, invariant violé) → FAILED."""


class ItemFilterError(PermanentFilterError):
    """Item unique malformé pour ce filtre (content_ids = [id])."""


class AIGatewayError(ModerationError):
    """Erreur de l'AI Gateway (côté `AIGatewayClient`)."""

    status_code: int | None

    def __init__(self, message: str = "", *, status_code: int | None = None) -> None:
        super().__init__(message or self.__class__.__name__)
        self.status_code = status_code

    def __str__(self) -> str:
        if self.status_code is not None:
            return f"{super().__str__()}: {self.status_code}"
        return super().__str__()


class AIGatewayUnavailableError(AIGatewayError):
    """Timeout / 408 / 429 / 5xx / erreur connexion → transitoire."""


class AIGatewayBudgetExceededError(AIGatewayError):
    """402 — budget épuisé → transitoire avec log `error`."""


class AIGatewayBadRequestError(AIGatewayError):
    """400/401/403/404/422 — requête invalide → permanent."""


class AIGatewayBadResponseError(AIGatewayError):
    """Réponse non conforme (JSON/format invalide) → transitoire."""


__all__ = [
    "ModerationError",
    "InvalidJobPayloadError",
    "PublishError",
    "FilterError",
    "TransientFilterError",
    "FilterTimeoutError",
    "PermanentFilterError",
    "ItemFilterError",
    "AIGatewayError",
    "AIGatewayUnavailableError",
    "AIGatewayBudgetExceededError",
    "AIGatewayBadRequestError",
    "AIGatewayBadResponseError",
]
