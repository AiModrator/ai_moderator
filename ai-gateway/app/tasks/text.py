"""Tâche de modération texte (main.md §5.4)."""

from __future__ import annotations

import json

from app.prompt.templates import get_template
from app.providers.base import ProviderResponse
from app.schemas.enums import MediaType
from app.tasks.base import AiTaskSpecification


class TextModerationTask(AiTaskSpecification):
    """Tâche de modération texte (batch, un appel par classe + sous-lots).

    - Items non applicables (`content` vide) → SKIPPED (géré au niveau Worker)
    - Texte envoyé au LLM : prompt système + JSON items `{id, text}`
    - Réponse validée via `ResponseValidator`
    """

    def build_prompt(self, items: list[dict]) -> list[dict]:
        """Construit les messages pour l'endpoint chat/completions.

        Format OpenAI : [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        template = get_template(self.risk_class, MediaType.TEXT, "v1")

        system_prompt = template.system_template.format(
            **{
                "class": self.risk_class,
                "definition": template.system_template.split("Définition de la classe : ")[1].split("\n")[0]
                if "Définition de la classe :" in template.system_template
                else "Définition non disponible",
                "score_scale": "Score ∈ [0, 1] : 0 = absence, 1 = certitude maximale",
                "output_schema": template.output_schema,
            }
        )

        # Construire le JSON des items pour l'utilisateur
        items_json = json.dumps(
            [{"id": item["id"], "text": item.get("content", "")} for item in items],
            ensure_ascii=False,
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": items_json},
        ]

    def parse(
        self,
        raw_text: str,
        item_ids: list[str],
        model: str,
    ) -> ProviderResponse:
        """Parse la réponse LLM via ResponseValidator."""
        validated = self._validator.validate(raw_text, item_ids)
        return ProviderResponse(
            raw_text=validated.model_dump_json(),
            input_tokens=0,  # sera rempli par le provider
            output_tokens=0,
            latency_ms=0,
            model=model,
        )


__all__ = ["TextModerationTask"]
