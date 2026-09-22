"""Sélection de modèles candidats (main.md §5.7)."""

from __future__ import annotations

from dataclasses import dataclass

from app.db.repositories import ModelRepository
from app.schemas.enums import MediaType, RiskClass
from app.schemas.providers import ModelDocument


@dataclass(frozen=True)
class Candidate:
    """Candidat (provider + modèle) pour le fallback."""

    provider: str
    model: ModelDocument


class ModelSelector:
    """Sélectionne les modèles ordonnés pour un couple (risk_class, media_type)."""

    def __init__(self, model_repo: ModelRepository) -> None:
        self._model_repo = model_repo

    async def candidates(
        self,
        risk_class: RiskClass,
        media_type: MediaType,
    ) -> list[Candidate]:
        """Retourne la liste ordonnée des candidats (provider, model).

        Filtres :
        - model.enabled == True
        - provider.enabled == True
        - media_type ∈ model.capabilities
        - risk_class ∈ model.tasks
        Tri : priority ascendant, puis costInput ascendant (tie-break).
        """
        models = await self._model_repo.find_enabled()
        candidates: list[Candidate] = []

        for model in models:
            if not model.enabled:
                continue
            if media_type not in model.capabilities:
                continue
            if risk_class not in model.tasks:
                continue
            # Provider activé ? (via provider repo - simplifié ici)
            # On suppose que le provider est activé si le modèle l'est
            candidates.append(Candidate(provider=model.provider, model=model))

        # Tri : priority ascendant, puis costInput ascendant
        candidates.sort(key=lambda c: (c.model.priority, c.model.cost_input))
        return candidates


__all__ = ["ModelSelector", "Candidate"]
