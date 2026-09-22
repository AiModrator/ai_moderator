"""Package tasks."""

from __future__ import annotations

from app.tasks.base import AiTaskSpecification
from app.tasks.image import ImageModerationTask
from app.tasks.registry import TASK_REGISTRY, get_task
from app.tasks.text import TextModerationTask

__all__ = [
    "AiTaskSpecification",
    "ImageModerationTask",
    "TextModerationTask",
    "TASK_REGISTRY",
    "get_task",
]
