"""Tests d'intégration du `UsageMeter` (MongoDB réel)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.config.settings import Settings
from app.db import create_mongo_client, get_database
from app.usage.usage_meter import UsageMeter


@pytest.mark.integration
async def test_record_and_query():
    settings = Settings(
        encryption_key="a" * 44,
        gateway_api_key="g",
        admin_api_key="a",
        log_format="console",
    )
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    await db.usage.delete_many({})
    meter = UsageMeter(db)

    now = datetime.now(UTC)
    await meter.record(
        request_id="req-1",
        timestamp=now,
        account_id="acc-1",
        provider="openrouter",
        model="meta-llama/llama-3-8b",
        risk_class="TOXICITY",
        media_type="text",
        status="success",
        input_tokens=100,
        output_tokens=50,
        latency_ms=200,
        estimated_cost=0.001,
        error=None,
    )
    await meter.record(
        request_id="req-2",
        timestamp=now,
        account_id="acc-1",
        provider="openrouter",
        model="meta-llama/llama-3-8b",
        risk_class="SPAM",
        media_type="text",
        status="success",
        input_tokens=200,
        output_tokens=30,
        latency_ms=150,
        estimated_cost=0.002,
        error=None,
    )

    # Aggregate sans group_by
    results = await meter.query(account_id="acc-1")
    assert len(results) == 1
    agg = results[0]
    assert agg["totalRequests"] == 2
    assert agg["totalInputTokens"] == 300
    assert agg["totalOutputTokens"] == 80
    assert agg["totalCost"] == 0.003
    assert agg["totalErrors"] == 0

    # Aggregate group_by provider
    results = await meter.query(account_id="acc-1", group_by="provider")
    assert len(results) == 1
    assert results[0]["_id"] == "openrouter"
    assert results[0]["totalRequests"] == 2

    client.close()


@pytest.mark.integration
async def test_query_with_filters():
    settings = Settings(
        encryption_key="a" * 44,
        gateway_api_key="g",
        admin_api_key="a",
        log_format="console",
    )
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    await db.usage.delete_many({})
    meter = UsageMeter(db)

    now = datetime.now(UTC)
    await meter.record(
        request_id="req-a",
        timestamp=now - timedelta(days=1),
        account_id="acc-filter",
        provider="openrouter",
        model="m1",
        risk_class="TOXICITY",
        media_type="text",
        status="success",
        input_tokens=10,
        output_tokens=5,
        latency_ms=10,
        estimated_cost=0.0001,
        error=None,
    )
    await meter.record(
        request_id="req-b",
        timestamp=datetime.now(UTC),
        account_id="acc-filter",
        provider="openrouter",
        model="m1",
        risk_class="TOXICITY",
        media_type="text",
        status="provider_error",
        input_tokens=10,
        output_tokens=5,
        latency_ms=5000,
        estimated_cost=0.0,
        error="timeout",
    )

    # Filtre par date
    from_dt = datetime.now(UTC) - timedelta(hours=1)
    results = await meter.query(account_id="acc-filter", from_dt=from_dt)
    assert len(results) == 1
    assert results[0]["totalRequests"] == 1
    assert results[0]["totalErrors"] == 1  # le second doc a error

    # Filtre par compte (différent)
    results = await meter.query(account_id="acc-autre")
    assert len(results) == 1
    assert results[0]["totalRequests"] == 0

    client.close()
