"""Spécification abstraite d'une tâche de modération IA (main.md §5.4, §5.5)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.prompt.registry import PromptRegistry
from app.providers.base import ProviderResponse
from app.schemas.enums import MediaType, RiskClass
from app.validation.response_validator import ResponseValidator


class AiTaskSpecification(ABC):
    """Spécification d'une tâche de modération IA.

    Définit comment construire le prompt et parser la réponse pour un couple
    (risk_class, media_type).
    """

    def __init__(
        self,
        risk_class: RiskClass,
        media_type: MediaType,
        prompts: PromptRegistry,
        validator: ResponseValidator,
    ) -> None:
        self.risk_class = risk_class
        self.media_type = media_type
        self._prompts = prompts
        self._validator = validator

    @property
    def key(self) -> tuple[RiskClass, MediaType]:
        return (self.risk_class, self.media_type)

    @abstractmethod
    def build_prompt(self, items: list[dict]) -> list[dict]:
        """Construit la liste de messages (format provider) pour un lot d'items.

        Args:
            items: Liste d'items avec `id` et `content` (texte ou URL image)

        Returns:
            Liste de messages au format provider (ex: OpenAI chat completions)
        """
        ...

    @abstractmethod
    def parse(
        self,
        raw_text: str,
        item_ids: list[str],
        model: str,
    ) -> ProviderResponse:
        """Parse la réponse brute du provider.

        Args:
            raw_text: Texte brut retourné par le provider
            item_ids: IDs des items envoyés (pour mapping)
            model: Nom du modèle utilisé

        Returns:
            ProviderResponse avec raw_text, tokens, latence, modèle
        """
        ...


__all__ = ["AiTaskSpecification"]
