"""Repository pour les budgets (collection `budgets`)."""

from __future__ import annotations

from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from app.config.settings import Settings


class BudgetRepository:
    """Accès à la collection `budgets` (atomique via `$inc`)."""

    def __init__(
        self, collection: AsyncIOMotorCollection, settings: Settings
    ) -> None:
        self._col = collection
        self._default_limit = settings.budget_default_monthly_limit

    async def get_or_create(self, account_id: str) -> dict:
        """Récupère ou crée un budget pour un compte."""
        doc = await self._col.find_one({"accountId": account_id})
        if doc:
            # Vérifier si la période a expiré (> 30 jours)
            period_start = doc.get("periodStart")
            if period_start:
                # Ensure period_start is offset-aware
                if period_start.tzinfo is None:
                    period_start = period_start.replace(tzinfo=UTC)
                if (datetime.now(UTC) - period_start).days >= 30:
                    await self.reset_period(account_id)
                    doc = await self._col.find_one({"accountId": account_id})
            return doc
        # Créer budget implicite
        new_doc = {
            "accountId": account_id,
            "currency": "USD",
            "monthlyLimit": self._default_limit,
            "warningThresholdPct": 80,
            "consumed": 0.0,
            "periodStart": datetime.now(UTC),
            "updatedAt": datetime.now(UTC),
        }
        await self._col.insert_one(new_doc)
        return new_doc

    async def increment_consumed(self, account_id: str, amount: float) -> dict:
        """Incrémente le budget consommé atomiquement ($inc)."""
        if amount <= 0:
            return await self.get_or_create(account_id)
        # get_or_create assure l'existence
        await self.get_or_create(account_id)
        result = await self._col.find_one_and_update(
            {"accountId": account_id},
            {"$inc": {"consumed": amount}, "$set": {"updatedAt": datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        return result

    async def reset_period(self, account_id: str) -> dict:
        """Remet à zéro la période courante."""
        result = await self._col.find_one_and_update(
            {"accountId": account_id},
            {
                "$set": {
                    "consumed": 0.0,
                    "periodStart": datetime.now(UTC),
                    "updatedAt": datetime.now(UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            # Si le budget n'existait pas, le créer
            return await self.get_or_create(account_id)
        return result

    async def set_limits(
        self, account_id: str, monthly_limit: float, warning_threshold_pct: int = 80
    ) -> dict:
        """Définit les limites du budget."""
        await self.get_or_create(account_id)
        result = await self._col.find_one_and_update(
            {"accountId": account_id},
            {
                "$set": {
                    "monthlyLimit": monthly_limit,
                    "warningThresholdPct": warning_threshold_pct,
                    "updatedAt": datetime.now(UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return result

    async def get(self, account_id: str) -> dict | None:
        """Récupère le budget sans le créer."""
        return await self._col.find_one({"accountId": account_id})


__all__ = ["BudgetRepository"]
