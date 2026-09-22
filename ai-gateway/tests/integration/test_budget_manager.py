"""Tests d'intégration du `BudgetManager` (MongoDB réel)."""

from __future__ import annotations

import asyncio

import pytest

from app.budget.budget_manager import BudgetManager
from app.config.settings import Settings
from app.db import create_mongo_client, get_database
from app.db.repositories import BudgetRepository


@pytest.fixture
async def budget_manager(settings: Settings):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    # Nettoyage
    await db.budgets.delete_many({})
    await db.usage.delete_many({})
    await db.models.delete_many({})
    await db.providers.delete_many({})
    bm = BudgetManager(db, Settings(
        encryption_key="a" * 44,
        gateway_api_key="g",
        admin_api_key="a",
        budget_default_monthly_limit=100.0,
        log_format="console",
    ))
    yield bm
    client.close()


@pytest.mark.integration
async def test_get_or_create(budget_manager: BudgetManager):
    budget = await budget_manager._repo.get_or_create("acc-1")
    assert budget["accountId"] == "acc-1"
    assert budget["monthlyLimit"] == 100.0
    assert budget["consumed"] == 0.0

    # Second call returns same
    budget2 = await budget_manager._repo.get_or_create("acc-1")
    assert budget2["_id"] == budget["_id"]


@pytest.mark.integration
async def test_increment_consumed_atomic():
    from app.config.settings import Settings
    from app.db import create_mongo_client, get_database

    settings = Settings(
        encryption_key="a" * 44,
        gateway_api_key="g",
        admin_api_key="a",
        log_format="console",
    )
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    await db.budgets.delete_many({})
    repo = BudgetRepository(db.budgets, settings)

    await repo.get_or_create("acc-atomic")
    await asyncio.gather(*[repo.increment_consumed("acc-atomic", 1.0) for _ in range(10)])
    budget = await repo.get("acc-atomic")
    assert budget["consumed"] == 10.0
    client.close()


@pytest.mark.integration
async def test_reset_period():
    from app.config.settings import Settings
    from app.db import create_mongo_client, get_database

    settings = Settings(
        encryption_key="a" * 44,
        gateway_api_key="g",
        admin_api_key="a",
        log_format="console",
    )
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    await db.budgets.delete_many({})
    repo = BudgetRepository(db.budgets, settings)

    await repo.get_or_create("acc-reset")
    repo2 = BudgetRepository(db.budgets, Settings(
        encryption_key="a" * 44,
        gateway_api_key="g",
        admin_api_key="a",
        log_format="console",
    ))
    await repo2.increment_consumed("acc-reset", 50.0)
    budget = await repo2.reset_period("acc-reset")
    assert budget["consumed"] == 0.0
    client.close()


@pytest.mark.integration
async def test_can_afford_within_limit():
    from app.budget.budget_manager import BudgetManager
    from app.config.settings import Settings
    from app.db import create_mongo_client, get_database

    settings = Settings(
        encryption_key="a" * 44,
        gateway_api_key="g",
        admin_api_key="a",
        budget_default_monthly_limit=100.0,
        log_format="console",
    )
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    await db.budgets.delete_many({})
    bm = BudgetManager(db, settings)

    model = {"costInput": 0.2, "costOutput": 0.8, "maxOutputTokens": 500}
    # est_cost pour 1000 tokens
    est_cost = bm.estimate_cost(model, 1000)
    can = await bm.can_afford("acc-budget", model, est_cost)
    assert can is True

    # Dépasser la limite
    await db.budgets.update_one({"accountId": "acc-budget"}, {"$set": {"consumed": 99.0}})
    can = await bm.can_afford("acc-budget", model, 2.0)
    assert can is False

    client.close()
