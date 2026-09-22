"""Compteur d'usage (main.md §5.10)."""

from __future__ import annotations

from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories import UsageRepository


class UsageMeter:
    """Enregistre et agrège l'usage par requête."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = UsageRepository(db.usage)

    async def record(
        self,
        *,
        request_id: str,
        timestamp: datetime | None = None,
        account_id: str,
        provider: str,
        model: str,
        risk_class: str,
        media_type: str,
        status: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        estimated_cost: float,
        error: str | None = None,
    ) -> None:
        """Enregistre un enregistrement d'usage."""
        doc = {
            "requestId": request_id,
            "timestamp": timestamp or datetime.now(UTC),
            "accountId": account_id,
            "provider": provider,
            "model": model,
            "riskClass": risk_class,
            "mediaType": media_type,
            "status": status,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "latencyMs": latency_ms,
            "estimatedCost": estimated_cost,
            "error": error,
        }
        await self._repo.insert(doc)

    async def query(
        self,
        *,
        account_id: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        group_by: str | None = None,
    ) -> list[dict]:
        """Agrégation MongoDB sur l'usage."""
        return await self._repo.aggregate(
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
            group_by=group_by,
        )


__all__ = ["UsageMeter"]
