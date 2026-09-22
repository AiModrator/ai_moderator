"""Classes de base pour les adaptateurs de fournisseurs IA (main.md §5.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import BaseModel

from app.errors import ProviderError


@dataclass(frozen=True)
class RetryPolicy:
    """Politique de retry exponentiel (main.md §6)."""

    base_delay_ms: int = 500
    multiplier: float = 2.0
    max_delay_ms: int = 8000
    max_retries: int = 3

    # Codes de statut HTTP retryables
    retryable_statuses: ClassVar[frozenset[int]] = frozenset(
        {408, 429, 500, 502, 503, 504}
    )

    def delay_for(self, attempt: int) -> int:
        """Délai pour la tentative `attempt` (0-indexed), plafonné à `max_delay_ms`."""
        if attempt < 0:
            attempt = 0
        delay = self.base_delay_ms * (self.multiplier**attempt)
        return min(int(delay), self.max_delay_ms)

    def is_retryable(self, status_code: int) -> bool:
        """Vérifie si un code HTTP déclenche un retry."""
        return status_code in self.retryable_statuses


class ProviderRequest(BaseModel):
    """Requête envoyée à l'adaptateur fournisseur."""

    model_config = {"extra": "forbid"}

    model: str
    messages: list[dict]
    max_tokens: int
    timeout_sec: float
    retry_policy: RetryPolicy
    request_id: str
    account_id: str
    risk_class: str


class ProviderResponse(BaseModel):
    """Réponse brute du fournisseur (transport only)."""

    model_config = {"extra": "forbid"}

    raw_text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    model: str


# --- Exceptions spécifiques providers ---

class ProviderTransientError(ProviderError):
    """Erreur transitoire (réseau, timeout, 429, 5xx) → retry/fallback."""

    def __init__(self, message: str = "", *, status_code: int | None = None) -> None:
        super().__init__(message, status_code=status_code)


class ProviderRequestError(ProviderError):
    """Erreur permanente fournisseur (400, 401, 403, 404, 422) → pas de retry."""

    def __init__(self, message: str = "", *, status_code: int | None = None) -> None:
        super().__init__(message, status_code=status_code)


class ProviderQuotaError(ProviderError):
    """402 — quota fournisseur épuisé (permanent)."""

    def __init__(self, message: str = "", *, status_code: int | None = None) -> None:
        super().__init__(message, status_code=status_code)


class InvalidResponseError(ProviderError):
    """Réponse fournisseur non conforme après retries/fallback."""

    def __init__(self, message: str = "", *, status_code: int | None = None) -> None:
        super().__init__(message, status_code=status_code)


# --- Adaptateur abstrait ---


class ProviderAdapter(ABC):
    """Adaptateur transport vers un fournisseur IA.

    Rôle : authentification, mapping requête/réponse, comptage tokens,
    retry/timeout réseau. **Ne connaît ni budget, ni prompt, ni validation.**
    """

    KIND: ClassVar[str]  # "openrouter" | "test"

    def __init__(
        self,
        config: Any,  # ProviderDocument (avec clé déchiffrée pour l'adaptateur)
        client: Any,  # httpx.AsyncClient
        retry: RetryPolicy,
    ) -> None:
        self._config = config
        self._client = client
        self._retry = retry

    @abstractmethod
    async def run(self, req: ProviderRequest) -> ProviderResponse:
        """Exécute la requête avec retry/timeout, retourne réponse normalisée."""
        ...


__all__ = [
    "RetryPolicy",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderAdapter",
    "ProviderTransientError",
    "ProviderRequestError",
    "ProviderQuotaError",
    "InvalidResponseError",
]
