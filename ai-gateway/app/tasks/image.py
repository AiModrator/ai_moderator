"""Tâche de modération image (main.md §5.5)."""

from __future__ import annotations

from app.prompt.templates import get_template
from app.providers.base import ProviderResponse
from app.schemas.enums import MediaType
from app.tasks.base import AiTaskSpecification


class ImageModerationTask(AiTaskSpecification):
    """Tâche de modération image (batch, un appel par image + classe).

    - Un message par image : system prompt + image_url
    - Réponse validée via ResponseValidator
    """

    def build_prompt(self, items: list[dict]) -> list[dict]:
        """Construit les messages pour un lot d'images.

        Format OpenAI vision : un message user avec image_url par image.
        Ici on retourne un prompt système unique ; l'adaptateur gère l'envoi par image.
        """
        template = get_template(self.risk_class, MediaType.IMAGE, "v1")

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

        return [{"role": "system", "content": system_prompt}]

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
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
            model=model,
        )


__all__ = ["ImageModerationTask"]
