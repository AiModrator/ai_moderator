"""Fixtures partagées des tests de l'AI Gateway."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.config.security import FernetCipher
from app.config.settings import Settings
from app.db import create_mongo_client, ensure_indexes, get_database
from app.db.repositories import ModelRepository, ProviderRepository, UsageRepository

_settings_call_count = 0


@pytest.fixture
def settings() -> Settings:
    """Settings de test : clé Fernet générée, MongoDB localhost."""
    global _settings_call_count
    _settings_call_count += 1
    key = Fernet.generate_key().decode()
    print(f"[DEBUG settings fixture] Call #{_settings_call_count} Generated key: {key[:20]}...")
    return Settings(
        encryption_key=key,
        gateway_api_key="test-gateway-key",
        admin_api_key="test-admin-key",
        log_format="console",
        log_level="DEBUG",
    )


@pytest.fixture
async def clean_db(settings: Settings):
    """Nettoie les collections de test avant chaque test et crée les index."""
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    await db.providers.delete_many({})
    await db.models.delete_many({})
    await db.budgets.delete_many({})
    await db.usage.delete_many({})
    await ensure_indexes(db, settings)
    yield db
    client.close()


@pytest.fixture
async def provider_repo(settings: Settings, clean_db):
    """Repository Provider avec DB nettoyée."""
    cipher = FernetCipher(settings.encryption_key)
    repo = ProviderRepository(clean_db.providers, cipher)
    yield repo


@pytest.fixture
async def model_repo(clean_db):
    """Repository Model avec DB nettoyée."""
    repo = ModelRepository(clean_db.models)
    yield repo


@pytest.fixture
async def usage_repo(clean_db):
    """Repository Usage avec DB nettoyée."""
    repo = UsageRepository(clean_db.usage)
    yield repo
