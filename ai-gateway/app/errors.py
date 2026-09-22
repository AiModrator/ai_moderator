"""Hiérarchie d'erreurs de l'AI Gateway (main.md §10).

Le mapping HTTP est contractuel avec le Moderation Service :
- 402 → `BudgetExceededError` (transitoire)
- 429/503 → `ProviderUnavailableError` (transitoire)
- 502 → `ProviderBadResponseError` (transitoire)
- 400/401/422 → `InvalidRequestError` / `UnauthorizedError` / `ValidationErrorBody`
"""

from __future__ import annotations

from typing import ClassVar


class GatewayError(Exception):
    """Racine de toutes les erreurs du gateway."""

    status_code: ClassVar[int] = 500

    def __init__(self, message: str = "", *, status_code: int | None = None) -> None:
        super().__init__(message or self.__class__.__name__)
        if status_code is not None:
            self.status_code = status_code


# ----- Erreurs de contrat entrant (Moderation Service → Gateway) -----

class InvalidRequestError(GatewayError):
    """400 — classe/média/items invalides."""

    status_code = 400


class UnauthorizedError(GatewayError):
    """401 — `GATEWAY_API_KEY` manquante/invalide."""

    status_code = 401


class BudgetExceededError(GatewayError):
    """402 — budget épuisé / aucun modèle abordable (transitoire)."""

    status_code = 402


class ValidationErrorBody(GatewayError):
    """422 — corps invalide (Pydantic)."""

    status_code = 422


# ----- Erreurs fournisseurs (ProviderAdapter → Router) -----

class ProviderError(GatewayError):
    """Erreur générique venant d'un fournisseur."""

    status_code = 503


class ProviderTransientError(ProviderError):
    """408/429/5xx/timeout/réseau → retryable/fallbackable."""

    status_code = 503


class ProviderRequestError(ProviderError):
    """400/401/403/404/422 fournisseur → permanent (jamais retry)."""

    status_code = 502


class ProviderQuotaError(ProviderError):
    """402 fournisseur → permanent, log error."""

    status_code = 402


class ProviderUnavailableError(ProviderError):
    """503 — tous fournisseurs/modèles en échec."""

    status_code = 503


class ProviderBadResponseError(ProviderError):
    """502 — réponse fournisseur non conforme après retries/fallback."""

    status_code = 502


# ----- Validation réponse LLM -----

class InvalidResponseError(ProviderError):
    """Réponse LLM non validée par ResponseValidator (retry/fallback)."""

    status_code = 502


__all__ = [
    "GatewayError",
    "InvalidRequestError",
    "UnauthorizedError",
    "BudgetExceededError",
    "ValidationErrorBody",
    "ProviderError",
    "ProviderTransientError",
    "ProviderRequestError",
    "ProviderQuotaError",
    "ProviderUnavailableError",
    "ProviderBadResponseError",
    "InvalidResponseError",
]
