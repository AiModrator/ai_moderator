"""Tests d'intégration du `UsageRepository` (MongoDB réel)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.db.repositories import UsageRepository


@pytest.mark.integration
async def test_insert_and_aggregate(usage_repo: UsageRepository) -> None:
    now = datetime.now(UTC)
    await usage_repo.insert(
        {
            "requestId": "req-1",
            "timestamp": now,
            "accountId": "acc-1",
            "provider": "openrouter",
            "model": "meta-llama/llama-3-8b",
            "riskClass": "TOXICITY",
            "mediaType": "text",
            "status": "success",
            "inputTokens": 100,
            "outputTokens": 50,
            "latencyMs": 200,
            "estimatedCost": 0.001,
            "error": None,
        }
    )
    await usage_repo.insert(
        {
            "requestId": "req-2",
            "timestamp": now,
            "accountId": "acc-1",
            "provider": "openrouter",
            "model": "meta-llama/llama-3-8b",
            "riskClass": "SPAM",
            "mediaType": "text",
            "status": "success",
            "inputTokens": 200,
            "outputTokens": 30,
            "latencyMs": 150,
            "estimatedCost": 0.002,
            "error": None,
        }
    )

    # Aggregate sans group_by
    results = await usage_repo.aggregate(account_id="acc-1")
    assert len(results) == 1
    agg = results[0]
    assert agg["totalRequests"] == 2
    assert agg["totalInputTokens"] == 300
    assert agg["totalOutputTokens"] == 80
    assert agg["totalCost"] == 0.003
    assert agg["totalErrors"] == 0

    # Aggregate group_by provider
    results = await usage_repo.aggregate(account_id="acc-1", group_by="provider")
    assert len(results) == 1
    assert results[0]["_id"] == "openrouter"
    assert results[0]["totalRequests"] == 2


@pytest.mark.integration
async def test_aggregate_with_filters(usage_repo: UsageRepository) -> None:
    now = datetime.now(UTC)
    await usage_repo.insert(
        {
            "requestId": "req-a",
            "timestamp": now - timedelta(days=1),
            "accountId": "acc-filter",
            "provider": "openrouter",
            "model": "m1",
            "riskClass": "TOXICITY",
            "mediaType": "text",
            "status": "success",
            "inputTokens": 10,
            "outputTokens": 5,
            "latencyMs": 10,
            "estimatedCost": 0.0001,
            "error": None,
        }
    )
    await usage_repo.insert(
        {
            "requestId": "req-b",
            "timestamp": now,
            "accountId": "acc-filter",
            "provider": "openrouter",
            "model": "m1",
            "riskClass": "TOXICITY",
            "mediaType": "text",
            "status": "provider_error",
            "inputTokens": 10,
            "outputTokens": 5,
            "latencyMs": 5000,
            "estimatedCost": 0.0,
            "error": "timeout",
        }
    )

    # Debug: check what's in the DB
    from app.config.settings import Settings
    from app.db import create_mongo_client, get_database
    client = create_mongo_client(Settings(
        encryption_key="a" * 44,
        gateway_api_key="dummy",
        admin_api_key="dummy",
    ))
    db = get_database(client, Settings(
        encryption_key="a" * 44,
        gateway_api_key="dummy",
        admin_api_key="dummy",
    ))
    docs = await db.usage.find({"accountId": "acc-filter"}).to_list(length=10)
    print(f"[DEBUG] Docs in DB: {len(docs)}")
    for d in docs:
        print(f"  {d['requestId']}: timestamp={d['timestamp']}, error={d.get('error')}")
    client.close()

    # Filtre par date : ne garde que req-b (timestamp = now)
    from_dt = now - timedelta(hours=1)
    results = await usage_repo.aggregate(account_id="acc-filter", from_dt=from_dt)
    print(f"[DEBUG] Aggregate results: {len(results)}")
    assert len(results) == 1
    assert results[0]["totalRequests"] == 1
    assert results[0]["totalErrors"] == 1  # le second doc a error="timeout"

    # Filtre par compte (différent)
    results = await usage_repo.aggregate(account_id="acc-autre")
    assert len(results) == 0  # aucun document ne correspond
