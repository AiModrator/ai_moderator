"""Registre des prompts versionnés (main.md §5.4)."""

from __future__ import annotations

from app.prompt.templates import PromptTemplate, get_template, list_versions
from app.schemas.enums import MediaType, RiskClass


class PromptRegistry:
    """Registre centralisé des templates de prompt versionnés.

    Centralise l'accès aux prompts par (risk_class, media_type, version).
    """

    def get(
        self,
        risk_class: RiskClass,
        media_type: MediaType,
        version: str = "latest",
    ) -> PromptTemplate:
        """Retourne le template pour la classe, média et version donnés.

        Args:
            risk_class: Classe de risque
            media_type: Type de média
            version: Version du template ("latest" ou explicite)

        Returns:
            PromptTemplate

        Raises:
            KeyError: si template introuvable
        """
        return get_template(risk_class, media_type, version)

    def list_versions(self, risk_class: RiskClass, media_type: MediaType) -> list[str]:
        """Liste les versions disponibles."""
        return list_versions(risk_class, media_type)


__all__ = ["PromptRegistry"]
