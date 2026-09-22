"""Tests unitaires du `ModelSelector` (main.md §5.7)."""

from __future__ import annotations

import pytest

from app.routing.model_selector import ModelSelector
from app.schemas.providers import ModelDocument


class MockModelRepository:
    """Stub de repository pour tests unitaires."""

    def __init__(self, models: list):
        self._models = models

    async def find_enabled(self) -> list:
        return self._models


class TestModelSelector:
    @pytest.fixture
    def models(self):
        return [
            # Provider A, priority 10, cost 0.2
            ModelDocument(
                id="m1",
                provider="providerA",
                model="modelA",
                displayName="Model A",
                capabilities=["text"],
                tasks=["TOXICITY", "INSULT"],
                maxInputTokens=32000,
                maxOutputTokens=500,
                costInput=0.2,
                costOutput=0.8,
                priority=10,
                enabled=True,
            ),
            # Provider B, priority 5, cost 0.1 (plus prioritaire)
            ModelDocument(
                id="m2",
                provider="providerB",
                model="modelB",
                displayName="Model B",
                capabilities=["text"],
                tasks=["TOXICITY", "INSULT"],
                maxInputTokens=32000,
                maxOutputTokens=500,
                costInput=0.1,
                costOutput=0.5,
                priority=5,
                enabled=True,
            ),
            # Modèle désactivé
            ModelDocument(
                id="m3",
                provider="providerA",
                model="modelC",
                displayName="Model C",
                capabilities=["text"],
                tasks=["TOXICITY"],
                maxInputTokens=32000,
                maxOutputTokens=500,
                costInput=0.3,
                costOutput=1.0,
                priority=1,
                enabled=False,
            ),
            # Média image
            ModelDocument(
                id="m4",
                provider="providerA",
                model="modelD",
                displayName="Model D",
                capabilities=["image"],
                tasks=["VIOLENCE", "SEXUAL"],
                maxInputTokens=32000,
                maxOutputTokens=500,
                costInput=0.5,
                costOutput=1.0,
                priority=10,
                enabled=True,
            ),
            # Même provider, autre modèle
            ModelDocument(
                id="m5",
                provider="providerA",
                model="modelE",
                displayName="Model E",
                capabilities=["text"],
                tasks=["HATE_SPEECH"],
                maxInputTokens=32000,
                maxOutputTokens=500,
                costInput=0.15,
                costOutput=0.6,
                priority=8,
                enabled=True,
            ),
        ]

    @pytest.fixture
    def selector(self, models):
        return ModelSelector(MockModelRepository(models))

    @pytest.mark.asyncio
    async def test_candidates_filter_by_task_and_media(self, selector):
        """Filtre par risk_class (task) et media_type."""
        candidates = await selector.candidates("TOXICITY", "text")
        ids = {c.model.id for c in candidates}
        assert ids == {"m1", "m2"}  # m3 disabled, m4 image, m5 HATE_SPEECH

    @pytest.mark.asyncio
    async def test_candidates_filter_by_media(self, selector):
        """Filtre par media_type."""
        candidates = await selector.candidates("VIOLENCE", "image")
        ids = {c.model.id for c in candidates}
        assert ids == {"m4"}

    @pytest.mark.asyncio
    async def test_candidates_exclude_disabled(self, selector):
        """Exclut les modèles disabled."""
        candidates = await selector.candidates("TOXICITY", "text")
        ids = {c.model.id for c in candidates}
        assert "m3" not in ids  # disabled

    @pytest.mark.asyncio
    async def test_candidates_sorted_by_priority_then_cost(self, selector):
        """Tri par priority asc, puis costInput asc."""
        candidates = await selector.candidates("TOXICITY", "text")
        # m2 (priority 5) avant m1 (priority 10)
        assert candidates[0].model.id == "m2"
        assert candidates[1].model.id == "m1"

    @pytest.mark.asyncio
    async def test_candidates_tie_break_cost(self):
        """Test tie-break costInput quand priority égal."""
        from app.schemas.providers import ModelDocument

        models = [
            ModelDocument(id="mA", provider="p", model="a", displayName="A", capabilities=["text"], tasks=["TOXICITY"], costInput=0.3, costOutput=0.5, priority=5, enabled=True),
            ModelDocument(id="mB", provider="p", model="b", displayName="B", capabilities=["text"], tasks=["TOXICITY"], costInput=0.1, costOutput=0.5, priority=5, enabled=True),
        ]
        from app.routing.model_selector import ModelSelector
        selector = ModelSelector(MockModelRepository(models))
        candidates = await selector.candidates("TOXICITY", "text")
        assert candidates[0].model.id == "mB"  # coût plus bas
        assert candidates[1].model.id == "mA"

    @pytest.mark.asyncio
    async def test_candidates_empty_if_no_match(self, selector):
        """Retourne liste vide si aucun match."""
        candidates = await selector.candidates("SCAM", "text")
        assert candidates == []
