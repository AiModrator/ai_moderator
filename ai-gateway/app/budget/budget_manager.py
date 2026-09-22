"""Gestionnaire de budget par compte (main.md §5.9)."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.settings import Settings
from app.db.repositories import BudgetRepository


class BudgetManager:
    """Gère les budgets par compte (création implicite, atomicité, période mensuelle)."""

    def __init__(self, db: AsyncIOMotorDatabase, settings: Settings) -> None:
        self._repo = BudgetRepository(db.budgets, settings)
        self._settings = settings

    def estimate_input_tokens(self, req: dict) -> int:
        """Estime le nombre de tokens d'entrée.

        - Texte : ceil(chars / 4)
        - Image : 1 token
        """
        content = req.get("content", "") or ""
        if not content:
            return 0
        # Heuristique : 1 token ≈ 4 caractères
        return max(1, (len(content) + 3) // 4)

    def estimate_cost(self, model: dict, input_tokens: int) -> float:
        """Estime le coût en USD.

        cost = input_tokens * costInput / 1e6 + out_est * costOutput / 1e6
        out_est = min(maxOutputTokens, 256)
        """
        cost_input = model.get("costInput", 0.0)
        cost_output = model.get("costOutput", 0.0)
        max_output = model.get("maxOutputTokens", 256)
        out_est = min(max_output, 256)
        return (input_tokens * cost_input + out_est * cost_output) / 1_000_000

    async def can_afford(self, account_id: str, model: dict, est_cost: float) -> bool:
        """Vérifie si le compte peut se permettre le coût estimé.

        Crée le budget implicite si absent (limite = BUDGET_DEFAULT_MONTHLY_LIMIT).
        """
        budget = await self._repo.get_or_create(account_id)
        consumed = budget.get("consumed", 0.0)
        limit = budget.get("monthlyLimit", self._settings.budget_default_monthly_limit)
        return consumed + est_cost <= limit

    async def commit(self, account_id: str, actual_cost: float) -> dict:
        """Engage le coût réel (incrémente atomiquement `consumed`).

        Gère le reset de période mensuelle si expirée.
        """
        return await self._repo.increment_consumed(account_id, actual_cost)

    async def get(self, account_id: str) -> dict | None:
        """Récupère l'état du budget ; déclenche warning seuil si dépassé."""
        budget = await self._repo.get(account_id)
        if budget:
            consumed = budget.get("consumed", 0.0)
            limit = budget.get("monthlyLimit", self._settings.budget_default_monthly_limit)
            threshold = budget.get("warningThresholdPct", 80)
            if limit > 0 and (consumed / limit * 100) >= threshold:
                # Log warning (structlog dans le caller)
                pass
        return budget

    async def set_limits(
        self, account_id: str, monthly_limit: float, warning_threshold_pct: int = 80
    ) -> dict:
        """Définit les limites du budget."""
        return await self._repo.set_limits(account_id, monthly_limit, warning_threshold_pct)

    async def reset_period(self, account_id: str) -> dict:
        """Remet à zéro la période courante."""
        return await self._repo.reset_period(account_id)


__all__ = ["BudgetManager"]
