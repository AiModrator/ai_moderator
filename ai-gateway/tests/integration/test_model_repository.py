"""Tests d'intégration du `ModelRepository` (MongoDB réel)."""

from __future__ import annotations

import pytest
from pymongo.errors import DuplicateKeyError

from app.schemas.enums import MediaType, RiskClass
from app.schemas.providers import ModelDocument


@pytest.mark.integration
async def test_crud(model_repo) -> None:
    model = ModelDocument(
        id="test-model",
        provider="openrouter",
        model="meta-llama/llama-3-8b",
        displayName="Llama 3",
        capabilities=[MediaType.TEXT],
        tasks=[RiskClass.TOXICITY],
        maxInputTokens=32000,
        maxOutputTokens=500,
        costInput=0.2,
        costOutput=0.8,
        priority=10,
        enabled=True,
    )
    await model_repo.create(model)

    # get
    got = await model_repo.get("test-model")
    assert got is not None
    assert got.id == "test-model"
    assert got.provider == "openrouter"

    # update
    updated = await model_repo.update("test-model", priority=5, enabled=False)
    assert updated is not None
    assert updated.priority == 5
    assert updated.enabled is False

    # delete (soft)
    deleted = await model_repo.delete("test-model")
    assert deleted is True
    assert not any(m.id == "test-model" for m in await model_repo.find_enabled())
    got = await model_repo.get("test-model")
    assert got is not None
    assert got.enabled is False


@pytest.mark.integration
async def test_find_enabled_only_returns_enabled(model_repo) -> None:
    m1 = ModelDocument(id="m1", provider="p", model="m", displayName="M1", capabilities=[], tasks=[], enabled=True)
    m2 = ModelDocument(id="m2", provider="p", model="m", displayName="M2", capabilities=[], tasks=[], enabled=False)
    m3 = ModelDocument(id="m3", provider="p", model="m", displayName="M3", capabilities=[], tasks=[], enabled=True)
    await model_repo.create(m1)
    await model_repo.create(m2)
    await model_repo.create(m3)

    enabled = await model_repo.find_enabled()
    ids = {m.id for m in enabled}
    assert ids == {"m1", "m3"}


@pytest.mark.integration
async def test_duplicate_id_raises(model_repo) -> None:
    m = ModelDocument(id="dup", provider="p", model="m", displayName="M", capabilities=[], tasks=[])
    await model_repo.create(m)
    with pytest.raises(DuplicateKeyError):
        await model_repo.create(m)
