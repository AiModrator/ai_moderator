"""Routeur principal d'un appel de modération (main.md §5.8).

Orchestre : sélection modèles → budget → prompt → appel provider → validation →
fallback/retry → commit budget/usage → mapping erreurs HTTP.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.budget.budget_manager import BudgetManager
from app.errors import (
    BudgetExceededError,
    InvalidResponseError,
    ProviderBadResponseError,
    ProviderQuotaError,
    ProviderRequestError,
    ProviderTransientError,
    ProviderUnavailableError,
)
from app.prompt.registry import PromptRegistry
from app.providers.base import ProviderRequest, RetryPolicy
from app.providers.registry import build_adapter
from app.routing.model_selector import ModelSelector
from app.schemas.moderation import ModerationRequest, ModerationResponse
from app.usage.usage_meter import UsageMeter
from app.validation.response_validator import ResponseValidator


class Router:
    """Orchestration complète d'un appel de modération (§5.8)."""

    def __init__(
        self,
        model_selector: ModelSelector,
        adapters: dict[str, Any],
        budget: BudgetManager,
        meter: UsageMeter,
        settings: Any,
    ) -> None:
        self._selector = model_selector
        self._adapters = adapters
        self._budget = budget
        self._meter = meter
        self._settings = settings
        self._prompts = PromptRegistry()
        self._validator = ResponseValidator()
        self._retry_policy = RetryPolicy(
            max_retries=settings.response_retry,
            base_delay_ms=settings.retry_base_delay_ms,
            multiplier=settings.retry_multiplier,
            max_delay_ms=settings.retry_max_delay_ms,
        )

    async def route(
        self,
        task: Any,  # AiTaskSpecification
        req: ModerationRequest,
    ) -> ModerationResponse:
        """Flux complet : sélection → budget → prompt → provider → validation → fallback."""
        # Simplifié : première classe
        risk_class = req.active_classes[0]
        media_type = req.items[0].attachments and "image" or "text"

        # 1. Candidats modèles
        candidates = await self._selector.candidates(risk_class, media_type)

        # 2. Boucle fallback
        last_error: Exception | None = None
        usage_recorded = False

        for candidate in candidates:
            provider_name = candidate.provider
            model = candidate.model

            # 3. Gate budget
            est_input = self._estimate_input_tokens(req)
            est_cost = self._budget.estimate_cost(model, est_input)

            if not await self._budget.can_afford(req.account_id or self._settings.default_account_id, model.__dict__, est_cost):
                last_error = BudgetExceededError("Budget exhausted for this model")
                continue

            # 4. Prompt
            prompt = task.build_prompt([{"id": item.content_id, "content": item.text or ""} for item in req.items])

            # 5. ProviderAdapter
            adapter = build_adapter(provider_name, model.__dict__, self._get_http_client(), self._settings)
            req_adapter = ProviderRequest(
                model=model.id,
                messages=prompt,
                max_tokens=model.max_output_tokens,
                timeout_sec=self._settings.ai_request_timeout_sec,
                retry_policy=RetryPolicy(max_retries=0),  # retry géré par Router
                request_id=str(uuid.uuid4()),
                account_id=req.account_id or self._settings.default_account_id,
                risk_class=str(req.active_classes[0]),
            )

            try:
                provider_resp = await adapter.run(req_adapter)
            except Exception as exc:
                if isinstance(exc, (ProviderTransientError,)):
                    last_error = exc
                    continue  # fallback
                # Erreurs permanentes → on sort de la boucle
                last_error = exc
                break

            # 6. Validation réponse
            try:
                validated = self._validator.validate(provider_resp.raw_text, [item.content_id for item in req.items])
            except InvalidResponseError:
                # Retry validation une fois sur le MÊME modèle
                try:
                    provider_resp = await adapter.run(req_adapter)
                    validated = self._validator.validate(provider_resp.raw_text, [item.content_id for item in req.items])
                except Exception:
                    last_error = ProviderBadResponseError("Response validation failed after retry")
                    continue  # fallback au modèle suivant

            # 7. Succès → commit budget + usage
            await self._budget.commit(req.account_id or self._settings.default_account_id, self._budget.estimate_cost(model, est_input))

            # UsageMeter record
            await self._meter.record(
                request_id=str(uuid.uuid4()),
                account_id=req.account_id or self._settings.default_account_id,
                provider=provider_name,
                model=model.id,
                risk_class=str(req.active_classes[0]),
                media_type=media_type.value,
                status="success",
                input_tokens=est_input,
                output_tokens=0,  # TODO: extraire du provider_resp
                latency_ms=0,  # TODO
                estimated_cost=self._budget.estimate_cost(model.__dict__, est_input),
                error=None,
            )
            usage_recorded = True

            # 8. Convertir en ModerationResponse finale
            return ModerationResponse(
                model=model.id,
                results=validated.results,
            )

        # Tous candidats épuisés
        if usage_recorded:
            # Ne devrait pas arriver ici
            raise ProviderUnavailableError("Unexpected state")

        # Mapping erreurs finales
        if isinstance(last_error, BudgetExceededError):
            raise last_error
        if isinstance(last_error, (ProviderRequestError, ProviderQuotaError)):
            raise ProviderBadResponseError(str(last_error))
        if isinstance(last_error, InvalidResponseError):
            raise ProviderBadResponseError(str(last_error))
        if isinstance(last_error, ProviderTransientError):
            raise ProviderUnavailableError(str(last_error))

        raise ProviderUnavailableError(str(last_error) if last_error else "No candidates available")

    def _estimate_input_tokens(self, req: ModerationRequest) -> int:
        total_chars = sum(len(item.text or "") for item in req.items)
        return max(1, (total_chars + 3) // 4)

    def _get_http_client(self):
        # TODO: retourner httpx.AsyncClient configuré
        pass


__all__ = ["Router"]
