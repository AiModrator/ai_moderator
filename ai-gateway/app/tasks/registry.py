"""Registre des tâches de modération (main.md §5.5)."""

from __future__ import annotations

from typing import Any

from app.tasks.image import ImageModerationTask
from app.tasks.text import TextModerationTask

TASK_REGISTRY: dict[tuple[str, str], type] = {
    ("SCAM", "text"): TextModerationTask,
    ("PHISHING", "text"): TextModerationTask,
    ("ADVERTISING", "text"): TextModerationTask,
    ("TOXICITY", "text"): TextModerationTask,
    ("INSULT", "text"): TextModerationTask,
    ("HARASSMENT", "text"): TextModerationTask,
    ("HATE_SPEECH", "text"): TextModerationTask,
    ("THREAT", "text"): TextModerationTask,
    ("HATE_SPEECH", "image"): ImageModerationTask,
    ("SEXUAL", "image"): ImageModerationTask,
    ("VIOLENCE", "image"): ImageModerationTask,
    ("ILLEGAL", "image"): ImageModerationTask,
    ("SELF_HARM", "image"): ImageModerationTask,
}


def get_task(
    risk_class: str,
    media_type: str,
    prompts: Any,
    validator: Any,
) -> Any:
    """Construit l'instance de tâche pour le couple (risk_class, media_type)."""
    key = (risk_class, media_type)
    if key not in TASK_REGISTRY:
        raise KeyError(f"Aucune tâche enregistrée pour {risk_class}/{media_type}")
    task_cls = TASK_REGISTRY[key]
    return task_cls(risk_class=risk_class, media_type=media_type, prompts=prompts, validator=validator)


__all__ = ["TASK_REGISTRY", "get_task"]
