"""Tests unitaires des tâches de modération (main.md §5.4, §5.5)."""

from __future__ import annotations

from app.prompt.registry import PromptRegistry
from app.tasks.image import ImageModerationTask
from app.tasks.text import TextModerationTask
from app.validation.response_validator import ResponseValidator


class TestTextModerationTask:
    def setup_method(self) -> None:
        self.prompts = PromptRegistry()
        self.validator = ResponseValidator()
        self.task = TextModerationTask(
            risk_class="TOXICITY",
            media_type="text",
            prompts=PromptRegistry(),
            validator=ResponseValidator(),
        )

    def test_build_prompt_structure(self) -> None:
        items = [
            {"id": "c-1", "content": "hello"},
            {"id": "c-2", "content": "world"},
        ]
        messages = self.task.build_prompt(items)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "TOXICITY" in messages[0]["content"]
        assert "c-1" in messages[1]["content"]
        assert "c-2" in messages[1]["content"]

    def test_parse_valid_response(self) -> None:
        raw = '{"model": "m", "results": [{"id": "c-1", "score": 0.9}]}'
        resp = self.task.parse(raw, ["c-1"], "test-model")
        assert resp.model == "test-model"
        assert "c-1" in resp.raw_text


class TestImageModerationTask:
    def setup_method(self) -> None:
        self.task = ImageModerationTask(
            risk_class="VIOLENCE",
            media_type="image",
            prompts=PromptRegistry(),
            validator=ResponseValidator(),
        )

    def test_build_prompt_system_only(self) -> None:
        items = [
            {"id": "img-1", "content": "https://example.com/img1.jpg"},
        ]
        messages = self.task.build_prompt(items)
        # ImageModerationTask ne renvoie que le system prompt
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert "VIOLENCE" in messages[0]["content"]

    def test_parse_valid_response(self) -> None:
        raw = '{"model": "m", "results": [{"id": "img-1", "score": 0.8}]}'
        resp = self.task.parse(raw, ["img-1"], "vision-model")
        assert resp.model == "vision-model"
        assert "img-1" in resp.raw_text
