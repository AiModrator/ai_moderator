"""Routes d'administration (main.md §2.2).

CRUD providers, models, budgets, usage. Auth via `X-Admin-Key`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel

from app.api.deps import require_admin_key
from app.config.settings import Settings
from app.db import create_mongo_client, get_database
from app.db.repositories import ModelRepository, ProviderRepository
from app.schemas.admin import (
    BudgetRead,
    BudgetSetLimits,
    ModelCreate,
    ModelRead,
    ProviderCreate,
    ProviderRead,
    ProviderUpdate,
    UsageAggregate,
    UsageAggregateByGroup,
)

router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
)


def get_settings(request: Request) -> Settings:
    """Dépendance : `Settings` stockés dans `app.state` par le bootstrap."""
    return request.app.state.settings


def _strip_oid(document: dict) -> dict:
    """Retire `_id` d'un document MongoDB avant validation (extra='forbid')."""
    return {k: v for k, v in document.items() if k != "_id"}


def _read_payload(model) -> dict:
    """Sérialise un document en camelCase (clés attendues par les schémas admin)."""
    return model.model_dump(mode="json", by_alias=True)


# --- Providers ---


@router.post("/providers", response_model=ProviderRead, status_code=status.HTTP_201_CREATED)
async def create_provider(
    req: ProviderCreate,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    from app.config.security import FernetCipher

    cipher = FernetCipher(settings.encryption_key)
    repo = ProviderRepository(db.providers, cipher)
    provider = await repo.create(
        name=req.name,
        kind=req.kind,
        display_name=req.display_name,
        base_url=req.base_url,
        api_key=req.api_key,
        enabled=req.enabled,
    )
    client.close()
    return ProviderRead.model_validate(_read_payload(provider))


@router.get("/providers", response_model=list[ProviderRead])
async def list_providers(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    from app.config.security import FernetCipher

    cipher = FernetCipher(settings.encryption_key)
    repo = ProviderRepository(db.providers, cipher)
    providers = await repo.find_enabled()
    client.close()
    return [ProviderRead.model_validate(_read_payload(p)) for p in providers]


@router.get("/providers/{name}", response_model=ProviderRead)
async def get_provider(
    name: Annotated[str, Path(description="Nom du provider")],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    from app.config.security import FernetCipher

    cipher = FernetCipher(settings.encryption_key)
    repo = ProviderRepository(db.providers, cipher)
    provider = await repo.get(name)
    client.close()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found") from None
    return ProviderRead.model_validate(_read_payload(provider))


@router.put("/providers/{name}", response_model=ProviderRead)
async def update_provider(
    name: Annotated[str, Path(description="Nom du provider")],
    req: ProviderUpdate,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    from app.config.security import FernetCipher

    cipher = FernetCipher(settings.encryption_key)
    repo = ProviderRepository(db.providers, cipher)
    provider = await repo.update(
        name,
        display_name=req.display_name,
        base_url=req.base_url,
        api_key=req.api_key,
        enabled=req.enabled,
    )
    client.close()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found") from None
    return ProviderRead.model_validate(_read_payload(provider))


@router.delete("/providers/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    name: Annotated[str, Path(description="Nom du provider")],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    from app.config.security import FernetCipher

    cipher = FernetCipher(settings.encryption_key)
    repo = ProviderRepository(db.providers, cipher)
    deleted = await repo.delete(name)
    client.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Provider not found") from None


# --- Models ---


@router.post("/models", response_model=ModelRead, status_code=status.HTTP_201_CREATED)
async def create_model(
    req: ModelCreate,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)

    repo = ModelRepository(db.models)
    from app.schemas.providers import ModelDocument

    await repo.create(ModelDocument.model_validate(req.model_dump(mode="json", by_alias=True)))
    model = await repo.get(req.id)
    client.close()
    return ModelRead.model_validate(_read_payload(model))


@router.get("/models", response_model=list[ModelRead])
async def list_models(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    client = create_mongo_client(settings)
    db = get_database(client, settings)

    repo = ModelRepository(db.models)
    models = await repo.find_enabled()
    client.close()
    return [ModelRead.model_validate(_read_payload(m)) for m in models]


@router.get("/models/{model_id}", response_model=ModelRead)
async def get_model(
    model_id: Annotated[str, Path(description="ID du modèle")],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)

    repo = ModelRepository(db.models)
    model = await repo.get(model_id)
    client.close()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found") from None
    return ModelRead.model_validate(_read_payload(model))


@router.put("/models/{model_id}", response_model=ModelRead)
async def update_model(
    model_id: Annotated[str, Path(description="ID du modèle")],
    req: ModelCreate,  # réutilise le même schéma
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)

    repo = ModelRepository(db.models)
    updated = await repo.update(model_id, **req.model_dump(exclude={"id", "provider", "model"}))
    client.close()
    if not updated:
        raise HTTPException(status_code=404, detail="Model not found") from None
    return ModelRead.model_validate(_read_payload(updated))


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: Annotated[str, Path(description="ID du modèle")],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)

    repo = ModelRepository(db.models)
    deleted = await repo.delete(model_id)
    client.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Model not found") from None


# --- Budgets ---


@router.get("/budgets/{account_id}", response_model=BudgetRead)
async def get_budget(
    account_id: Annotated[str, Path(description="ID du compte")],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    from app.budget.budget_manager import BudgetManager

    bm = BudgetManager(db, settings)
    budget = await bm.get(account_id)
    client.close()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found") from None
    return BudgetRead.model_validate(_strip_oid(budget))


@router.put("/budgets/{account_id}", response_model=BudgetRead)
async def set_budget_limits(
    account_id: Annotated[str, Path(description="ID du compte")],
    req: BudgetSetLimits,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    from app.budget.budget_manager import BudgetManager

    bm = BudgetManager(db, settings)
    budget = await bm.set_limits(account_id, req.monthly_limit, req.warning_threshold_pct)
    client.close()
    return BudgetRead.model_validate(_strip_oid(budget))


@router.post("/budgets/{account_id}/reset", response_model=BudgetRead)
async def reset_budget_period(
    account_id: Annotated[str, Path(description="ID du compte")],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    from app.budget.budget_manager import BudgetManager

    bm = BudgetManager(db, settings)
    budget = await bm.reset_period(account_id)
    client.close()
    return BudgetRead.model_validate(_strip_oid(budget))


# --- Usage ---


class UsageQueryParams(BaseModel):
    account_id: str | None = Query(default=None, description="Filtrer par compte")
    from_dt: str | None = Query(default=None, description="Date début ISO 8601")
    to_dt: str | None = Query(default=None, description="Date fin ISO 8601")
    group_by: str | None = Query(default=None, description="Grouper par: provider|model|riskClass|mediaType|status|day")


@router.get("/usage", response_model=list[UsageAggregate | UsageAggregateByGroup])
async def query_usage(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    params: Annotated[UsageQueryParams, Depends()],
):
    client = create_mongo_client(settings)
    db = get_database(client, settings)
    from app.usage.usage_meter import UsageMeter

    meter = UsageMeter(db)
    from_dt = None
    to_dt = None
    if params.from_dt:
        from datetime import UTC, datetime

        from_dt = datetime.fromisoformat(params.from_dt).replace(tzinfo=UTC)
    if params.to_dt:
        from datetime import UTC, datetime

        to_dt = datetime.fromisoformat(params.to_dt).replace(tzinfo=UTC)

    results = await meter.query(
        account_id=params.account_id,
        from_dt=from_dt,
        to_dt=to_dt,
        group_by=params.group_by,
    )
    normalized: list[dict] = []
    for result in results:
        if "_id" in result:
            entry = dict(result)
            group_value = entry.pop("_id")
            if group_value is not None:
                entry["group"] = group_value
            normalized.append(entry)
        else:
            normalized.append(result)
    client.close()
    return normalized


__all__ = ["router"]
