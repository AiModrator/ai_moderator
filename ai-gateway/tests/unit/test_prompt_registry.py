"""Tests unitaires du `PromptRegistry` et templates (main.md §5.4)."""

from __future__ import annotations

import pytest

from app.prompt.registry import PromptRegistry
from app.prompt.templates import CLASS_DEFINITIONS, PromptTemplate, get_template, list_versions


class TestPromptTemplates:
    def test_class_definitions_complete(self) -> None:
        # 12 classes attendues
        assert len(CLASS_DEFINITIONS) == 12
        for rc in [
            "SCAM", "PHISHING", "ADVERTISING", "TOXICITY", "INSULT", "HARASSMENT",
            "HATE_SPEECH", "THREAT", "VIOLENCE", "SEXUAL", "SELF_HARM", "ILLEGAL",
        ]:
            assert rc in CLASS_DEFINITIONS
            assert len(CLASS_DEFINITIONS[rc]) > 10

    def test_get_template_text_v1(self) -> None:
        tpl = get_template("TOXICITY", "text", "v1")
        assert isinstance(tpl, PromptTemplate)
        assert tpl.version == "v1"
        assert "{class}" in tpl.system_template
        assert "{definition}" in tpl.system_template
        assert "{score_scale}" in tpl.system_template
        assert "{output_schema}" in tpl.system_template

    def test_get_template_image_v1(self) -> None:
        tpl = get_template("VIOLENCE", "image", "v1")
        assert isinstance(tpl, PromptTemplate)
        assert tpl.version == "v1"

    def test_get_template_latest_alias(self) -> None:
        tpl_v1 = get_template("TOXICITY", "text", "v1")
        tpl_latest = get_template("TOXICITY", "text", "latest")
        assert tpl_latest.version == tpl_v1.version

    def test_get_template_unknown_version_fallback(self) -> None:
        # Version inconnue → fallback latest si v1 existe
        tpl = get_template("TOXICITY", "text", "v99")
        assert tpl.version == "v1"

    def test_get_template_unknown_class_raises(self) -> None:
        with pytest.raises(KeyError):
            get_template("UNKNOWN_CLASS", "text", "v1")

    def test_list_versions(self) -> None:
        versions = list_versions("TOXICITY", "text")
        assert "v1" in versions


class TestPromptRegistry:
    def test_get(self) -> None:
        reg = PromptRegistry()
        tpl = reg.get("TOXICITY", "text", "v1")
        assert isinstance(tpl, PromptTemplate)

    def test_list_versions(self) -> None:
        reg = PromptRegistry()
        versions = reg.list_versions("TOXICITY", "text")
        assert "v1" in versions
