"""Tests unitaires des schémas Pydantic (main.md §2.1, §3)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.enums import CLASS_MEDIA_CAPABILITIES, MediaType, RiskClass
from app.schemas.moderation import ModerationItem, ModerationRequest, ModerationResponse, ResultItem
from app.schemas.providers import ModelDocument, ProviderDocument, ProviderKind


class TestEnums:
    def test_risk_class_values(self) -> None:
        assert len(RiskClass) == 12
        assert RiskClass.SCAM.value == "SCAM"
        assert RiskClass.HATE_SPEECH.value == "HATE_SPEECH"

    def test_media_type_values(self) -> None:
        assert MediaType.TEXT.value == "text"
        assert MediaType.IMAGE.value == "image"

    def test_class_media_capabilities(self) -> None:
        # Classes texte seulement
        text_only = {
            RiskClass.SCAM, RiskClass.PHISHING, RiskClass.ADVERTISING,
            RiskClass.TOXICITY, RiskClass.INSULT, RiskClass.HARASSMENT,
            RiskClass.THREAT,
        }
        for rc in text_only:
            assert CLASS_MEDIA_CAPABILITIES[rc] == {MediaType.TEXT}

        # Classes texte + image
        text_image = {
            RiskClass.HATE_SPEECH, RiskClass.SEXUAL, RiskClass.VIOLENCE,
            RiskClass.ILLEGAL, RiskClass.SELF_HARM,
        }
        for rc in text_image:
            assert CLASS_MEDIA_CAPABILITIES[rc] == {MediaType.TEXT, MediaType.IMAGE}


class TestModerationItem:
    def test_valid(self) -> None:
        item = ModerationItem(id="c-1", content="hello")
        assert item.id == "c-1"
        assert item.content == "hello"

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModerationItem(id="", content="x")

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModerationItem(id="c-1", content="")


class TestModerationRequest:
    def test_valid_text(self) -> None:
        req = ModerationRequest(
            accountId="acc-1",
            activeClasses=[RiskClass.TOXICITY],
            mediaType="text",
            items=[{"id": "c-1", "content": "hello"}],
        )
        assert req.account_id == "acc-1"
        assert req.media_type == MediaType.TEXT
        assert len(req.items) == 1

    def test_valid_image(self) -> None:
        req = ModerationRequest(
            activeClasses=[RiskClass.HATE_SPEECH],
            mediaType="image",
            items=[{"id": "c-1", "content": "https://example.com/img.png"}],
        )
        assert req.media_type == MediaType.IMAGE

    def test_empty_items_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModerationRequest(mediaType="text", items=[])

    def test_duplicate_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModerationRequest(
                mediaType="text",
                items=[{"id": "c-1", "content": "a"}, {"id": "c-1", "content": "b"}],
            )

    def test_extra_field_rejected(self) -> None:  # extra="forbid"
        with pytest.raises(ValidationError):
            ModerationRequest(
                mediaType="text",
                items=[{"id": "c-1", "content": "x"}],
                extra_field="nope",
            )


class TestResultItem:
    def test_valid_score_bounds(self) -> None:
        ResultItem(id="c-1", score=0.0)
        ResultItem(id="c-1", score=1.0)
        ResultItem(id="c-1", score=0.5)

    def test_score_out_of_bounds_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ResultItem(id="c-1", score=-0.1)
        with pytest.raises(ValidationError):
            ResultItem(id="c-1", score=1.1)


class TestModerationResponse:
    def test_valid(self) -> None:
        resp = ModerationResponse(model="test-model", results=[ResultItem(id="c-1", score=0.9)])
        assert resp.model == "test-model"
        assert len(resp.results) == 1


class TestProviderDocument:
    def test_valid(self) -> None:
        doc = ProviderDocument(
            name="openrouter",
            kind=ProviderKind.OPENROUTER,
            displayName="OpenRouter",
            baseUrl="https://openrouter.ai/api/v1",
        )
        assert doc.name == "openrouter"
        assert doc.kind == ProviderKind.OPENROUTER


class TestModelDocument:
    def test_valid(self) -> None:
        doc = ModelDocument(
            id="m1",
            provider="openrouter",
            model="meta-llama/llama-3-8b",
            displayName="Llama 3",
            capabilities=[MediaType.TEXT],
            tasks=[RiskClass.TOXICITY],
        )
        assert doc.id == "m1"
        assert doc.provider == "openrouter"
