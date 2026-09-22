"""Fixtures partagées des tests de l'AI Gateway."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    """Settings de test : clé Fernet générée, MongoDB localhost."""
    key = Fernet.generate_key().decode()
    return Settings(
        encryption_key=key,
        gateway_api_key="test-gateway-key",
        admin_api_key="test-admin-key",
        log_format="console",
        log_level="DEBUG",
    )


@pytest.fixture
def fernet_key() -> str:
    """Clé Fernet de test."""
    return Fernet.generate_key().decode()
