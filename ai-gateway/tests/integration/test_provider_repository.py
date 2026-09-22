"""Tests d'intégration du `ProviderRepository` (MongoDB réel)."""

from __future__ import annotations

import pytest
from pymongo.errors import DuplicateKeyError

from app.schemas.providers import ProviderKind


@pytest.mark.integration
async def test_create_and_find_enabled(provider_repo, settings) -> None:
    await provider_repo.create(
        name="openrouter",
        kind=ProviderKind.OPENROUTER,
        display_name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-test-123",
    )
    providers = await provider_repo.find_enabled()
    assert len(providers) == 1
    p = providers[0]
    assert p.name == "openrouter"
    assert p.kind == ProviderKind.OPENROUTER
    assert p.api_key_encrypted == "sk-test-123"  # déchiffrée pour l'adaptateur


@pytest.mark.integration
async def test_get_masks_key_for_admin(provider_repo) -> None:
    await provider_repo.create(
        name="openrouter",
        kind=ProviderKind.OPENROUTER,
        display_name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-secret",
    )
    p = await provider_repo.get("openrouter")
    assert p is not None
    assert p.api_key_encrypted == "***"  # masquée pour l'admin


@pytest.mark.integration
async def test_duplicate_name_raises(provider_repo) -> None:
    await provider_repo.create(
        name="dup",
        kind=ProviderKind.TEST,
        display_name="Test",
        base_url="http://test",
    )
    with pytest.raises(DuplicateKeyError):
        await provider_repo.create(
            name="dup",
            kind=ProviderKind.TEST,
            display_name="Test 2",
            base_url="http://test2",
        )


@pytest.mark.integration
async def test_update_encrypts_new_key(provider_repo) -> None:
    await provider_repo.create(
        name="upd",
        kind=ProviderKind.TEST,
        display_name="Test",
        base_url="http://test",
        api_key="old-key",
    )
    await provider_repo.update("upd", api_key="new-key")
    providers = await provider_repo.find_enabled()
    p = next(x for x in providers if x.name == "upd")
    assert p.api_key_encrypted == "new-key"


@pytest.mark.integration
async def test_delete_soft_delete(provider_repo) -> None:
    await provider_repo.create(
        name="del",
        kind=ProviderKind.TEST,
        display_name="Test",
        base_url="http://test",
    )
    deleted = await provider_repo.delete("del")
    assert deleted is True
    providers = await provider_repo.find_enabled()
    assert not any(p.name == "del" for p in providers)
    # get renvoie quand même le doc (masqué)
    p = await provider_repo.get("del")
    assert p is not None
    assert p.enabled is False
