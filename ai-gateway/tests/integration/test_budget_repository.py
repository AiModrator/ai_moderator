"""Tests d'intégration du `BudgetRepository` (MongoDB réel)."""

from __future__ import annotations

import asyncio

import pytest

from app.config.settings import Settings
from app.db import create_mongo_client, get_database
from app.db.repositories import BudgetRepository


@pytest.fixture
def budget_repo(settings: Settings):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    repo = BudgetRepository(db.budgets, settings)
    yield repo
    client.close()


@pytest.mark.integration
async def test_get_or_create(budget_repo: BudgetRepository) -> None:
    budget = await budget_repo.get_or_create("acc-1")
    assert budget["accountId"] == "acc-1"
    assert budget["monthlyLimit"] == 100.0
    assert budget["consumed"] == 0.0

    # Second call returns same
    budget2 = await budget_repo.get_or_create("acc-1")
    assert budget2["_id"] == budget["_id"]


@pytest.mark.integration
async def test_increment_consumed_atomic(budget_repo: BudgetRepository) -> None:
    await budget_repo.get_or_create("acc-atomic")
    # Incréments concurrents
    await asyncio.gather(
        *[budget_repo.increment_consumed("acc-atomic", 1.0) for _ in range(10)]
    )
    budget = await budget_repo.get("acc-atomic")
    assert budget["consumed"] == 10.0


@pytest.mark.integration
async def test_increment_creates_if_missing(budget_repo: BudgetRepository) -> None:
    await budget_repo.increment_consumed("acc-new", 5.5)
    budget = await budget_repo.get("acc-new")
    assert budget is not None
    assert budget["consumed"] == 5.5


@pytest.mark.integration
async def test_reset_period(budget_repo: BudgetRepository) -> None:
    await budget_repo.get_or_create("acc-reset")
    await budget_repo.increment_consumed("acc-reset", 50.0)
    budget = await budget_repo.reset_period("acc-reset")
    assert budget["consumed"] == 0.0
    assert budget["periodStart"] is not None


@pytest.mark.integration
async def test_set_limits(budget_repo: BudgetRepository) -> None:
    await budget_repo.get_or_create("acc-limits")
    budget = await budget_repo.set_limits("acc-limits", monthly_limit=500.0, warning_threshold_pct=90)
    assert budget["monthlyLimit"] == 500.0
    assert budget["warningThresholdPct"] == 90


@pytest.mark.integration
async def test_get_without_create(budget_repo: BudgetRepository) -> None:
    budget = await budget_repo.get("acc-nonexistent")
    assert budget is None
