"""Repository pour l'usage (collection `usage`)."""

from __future__ import annotations

from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorCollection


class UsageRepository:
    """Accès à la collection `usage` (insert + agrégations)."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def insert(self, doc: dict) -> None:
        """Insère un enregistrement d'usage."""
        if "timestamp" not in doc:
            doc["timestamp"] = datetime.now(UTC)
        await self._col.insert_one(doc)

    async def aggregate(
        self,
        *,
        account_id: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        group_by: str | None = None,
    ) -> list[dict]:
        """Agrégation MongoDB sur l'usage."""
        match: dict = {}
        if account_id:
            match["accountId"] = account_id
        if from_dt or to_dt:
            ts_match: dict = {}
            if from_dt:
                ts_match["$gte"] = from_dt
            if to_dt:
                ts_match["$lte"] = to_dt
            match["timestamp"] = ts_match

        pipeline: list[dict] = [{"$match": match}]
        if group_by:
            group_id = f"${group_by}"
            pipeline.append(
                {
                    "$group": {
                        "_id": group_id,
                        "totalRequests": {"$sum": 1},
                        "totalInputTokens": {"$sum": "$inputTokens"},
                        "totalOutputTokens": {"$sum": "$outputTokens"},
                        "totalCost": {"$sum": "$estimatedCost"},
                        "totalErrors": {
                            "$sum": {
                                "$cond": [{"$ne": ["$error", None]}, 1, 0]
                            }
                        },
                    }
                }
            )
        else:
            pipeline.append(
                {
                    "$group": {
                        "_id": None,
                        "totalRequests": {"$sum": 1},
                        "totalInputTokens": {"$sum": "$inputTokens"},
                        "totalOutputTokens": {"$sum": "$outputTokens"},
                        "totalCost": {"$sum": "$estimatedCost"},
                        "totalErrors": {
                            "$sum": {
                                "$cond": [{"$ne": ["$error", None]}, 1, 0]
                            }
                        },
                    }
                }
            )
        pipeline.append({"$sort": {"_id": 1}})
        cursor = self._col.aggregate(pipeline)
        results = [doc async for doc in cursor]
        if not results and group_by:
            # Retourner un résultat par défaut avec des zéros quand group_by est spécifié
            # mais aucun document ne correspond
            return [{
                "totalRequests": 0,
                "totalInputTokens": 0,
                "totalOutputTokens": 0,
                "totalCost": 0.0,
                "totalErrors": 0,
            }]
        return results


__all__ = ["UsageRepository"]
