"""Tests d'intégration du bootstrap (main.md §12).

Vérifie :
- MongoDB injoignable → exit 1 + log error
- MongoDB OK → boot OK
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from app.config.settings import Settings
from app.db import check_mongo
from main import async_boot

# Set required environment variables for Settings validation
os.environ.setdefault("ENCRYPTION_KEY", "a" * 44)
os.environ.setdefault("GATEWAY_API_KEY", "test-key")
os.environ.setdefault("ADMIN_API_KEY", "test-key")


def _test_settings(**overrides) -> Settings:
    """Settings de test valides."""
    base = dict(
        log_format="console",
    )
    base.update(overrides)
    return Settings(**base)


@pytest.mark.integration
async def test_bootstrap_mongo_unreachable_exits():
    """MongoDB injoignable → SystemExit(1) + log error."""
    settings = _test_settings(
        mongodb_uri="mongodb://127.0.0.1:27018",  # port non écouté
        mongodb_db="ai_gateway_test",
    )

    with patch("main.check_mongo", new_callable=AsyncMock) as mock_check, \
         patch("main.create_mongo_client") as mock_create_client, \
         patch("main.get_database") as mock_get_db, \
         patch("main.ensure_indexes", new_callable=AsyncMock), \
         patch("main.create_router") as mock_create_router, \
         patch("main.create_app") as mock_create_app, \
         patch("main.uvicorn.Server") as mock_server_class:

        mock_check.return_value = False

        with pytest.raises(SystemExit) as excinfo:
            await async_boot()

        assert excinfo.value.code == 1


@pytest.mark.integration
async def test_bootstrap_mongo_ok():
    """MongoDB joignable → boot OK (ne pas exit)."""
    settings = _test_settings()

    # Mock MongoDB OK
    with patch("main.check_mongo", new_callable=AsyncMock) as mock_check, \
         patch("main.create_mongo_client") as mock_create_client, \
         patch("main.get_database") as mock_get_db, \
         patch("main.ensure_indexes", new_callable=AsyncMock) as mock_ensure_indexes, \
         patch("main.create_router") as mock_create_router, \
         patch("main.create_app") as mock_create_app, \
         patch("main.uvicorn.Server") as mock_server_class:

        mock_check.return_value = True
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        mock_server_instance = MagicMock()
        # serve() should not return (it runs forever), so we make it raise SystemExit
        async def mock_serve():
            raise SystemExit(0)
        mock_server_instance.serve = mock_serve
        mock_server_class.return_value = mock_server_instance

        with pytest.raises(SystemExit) as excinfo:
            await async_boot()

        assert excinfo.value.code == 0


@pytest.mark.integration
async def test_check_mongo_real():
    """Test check_mongo avec vrai MongoDB (skip si pas dispo)."""
    import os
    if not os.getenv("MONGO_TEST_AVAILABLE"):
        pytest.skip("MongoDB not available for integration test")

    settings = _test_settings(
        mongodb_uri="mongodb://localhost:27017",
        mongodb_db="ai_gateway_test",
    )

    client = AsyncIOMotorClient("mongodb://localhost:27017")
    ok = await check_mongo(client)
    assert ok is True
    client.close()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
