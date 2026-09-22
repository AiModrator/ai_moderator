"""Routes de modération par classe (main.md §7, §2.1).

`POST /v1/moderation/{riskClass}` avec validation entrée/sortie.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from app.api.deps import require_gateway_key
from app.errors import (
    BudgetExceededError,
    InvalidResponseError,
    ProviderRequestError,
    ProviderTransientError,
    ProviderUnavailableError,
)
from app.prompt.registry import PromptRegistry
from app.routing.router import Router
from app.schemas.enums import MediaType, RiskClass
from app.schemas.moderation import ModerationRequest, ModerationResponse
from app.tasks.registry import get_task
from app.validation.response_validator import ResponseValidator

router = APIRouter(
    prefix="/v1/moderation",
    tags=["moderation"],
    dependencies=[Depends(require_gateway_key)],
)


async def get_router(request: Request) -> Router:
    return request.app.state.router


@router.post(
    "/{risk_class}",
    response_model=ModerationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Requête invalide (classe/média/items)"},
        401: {"description": "Clé API manquante/invalide"},
        402: {"description": "Budget épuisé"},
        404: {"description": "Classe de risque inconnue"},
        422: {"description": "Corps de requête invalide (Pydantic)"},
        429: {"description": "Rate-limit fournisseur épuisé"},
        502: {"description": "Réponse fournisseur non conforme"},
        503: {"description": "Tous fournisseurs indisponibles"},
    },
)
async def moderate(
    risk_class: Annotated[RiskClass, Path(description="Classe de risque à modérer")],
    req: ModerationRequest,
    request: Request,
    app_router: Annotated[Router, Depends(get_router)],
) -> ModerationResponse:
    """Modère un lot de contenus pour une classe de risque donnée.

    - Valide que `mediaType` est supporté par la classe.
    - Construit la tâche via `TASK_REGISTRY`.
    - Appelle `Router.route` avec retry/fallback.
    - Retourne `ModerationResponse` (résultats agrégés).
    """
    # Validation mediaType vs classe
    from app.schemas.enums import CLASS_MEDIA_CAPABILITIES

    first_item = req.items[0] if req.items else None
    if first_item and first_item.attachments and any(a.type == "image" for a in first_item.attachments):
        media_type = MediaType.IMAGE
    else:
        media_type = MediaType.TEXT

    if media_type not in CLASS_MEDIA_CAPABILITIES.get(risk_class, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Media type {media_type} not supported for class {risk_class}",
        )

    # Construire la tâche
    try:
        prompts = PromptRegistry()
        validator = ResponseValidator()
        task = get_task(risk_class.value, media_type.value, prompts, validator)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No task registered for {risk_class}/{media_type}",
        ) from None

    try:
        response = await app_router.route(task, req)
    except Exception as exc:
        # Mapping erreurs → codes HTTP (§2.1)
        if isinstance(exc, ProviderRequestError):
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if isinstance(exc, ProviderTransientError):
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if isinstance(exc, InvalidResponseError):
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if isinstance(exc, BudgetExceededError):
            raise HTTPException(status_code=402, detail=str(exc)) from exc
        if isinstance(exc, ProviderUnavailableError):
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        # Erreurs non gérées → 500
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return response


__all__ = ["router"]
