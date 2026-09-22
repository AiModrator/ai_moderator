"""Bootstrap de l'AI Gateway (main.md §12).

Séquence de démarrage :
1. `Settings` (`.env.local` prioritaire) → logging structlog.
2. Vérification MongoDB (échec → log `error` + exit 1).
3. Création des index MongoDB.
4. Initialisation des composants core (Router, BudgetManager, UsageMeter, etc.).
5. FastAPI (uvicorn, `HTTP_PORT`) ; uvicorn gère les signaux.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import suppress

import uvicorn
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from app.api.health import router as health_router
from app.api.routes_moderation import router as moderation_router
from app.config.logging import configure_logging, get_logger
from app.config.settings import Settings
from app.db import check_mongo, create_mongo_client, get_database, ensure_indexes
from app.budget.budget_manager import BudgetManager
from app.usage.usage_meter import UsageMeter
from app.prompt.registry import PromptRegistry
from app.routing.router import Router
from app.routing.model_selector import ModelSelector
from app.db.repositories import ModelRepository
from app.db import check_mongo, create_mongo_client, get_database, ensure_indexes

VERSION = "0.1.0"


def create_router(settings: Settings, db) -> Router:
    """Construit le `Router` avec toutes ses dépendances."""
    budget = BudgetManager(db, settings)
    meter = UsageMeter(db)
    selector = ModelSelector(ModelRepository(db.models))
    return Router(
        model_selector=ModelSelector(ModelRepository(db.models)),
        adapters={},  # build_adapter sera appelé dynamiquement
        budget=budget,
        meter=UsageMeter(db),
        settings=settings,
    )


def create_app(
    settings: Settings | None = None, mongo_client: AsyncIOMotorClient | None = None
) -> FastAPI:
    """Fabrique l'application FastAPI avec `/health` et routes de modération."""
    settings = settings or Settings()
    mongo_client = mongo_client or create_mongo_client(settings)
    db = get_database(mongo_client, settings)

    app = FastAPI(title="ai-gateway", version=VERSION)
    app.state.settings = settings
    app.state.mongo_client = mongo_client
    app.state.db = db
    app.include_router(health_router)
    app.include_router(moderation_router)

    # Initialiser le router dans l'état de l'app (lazy au premier appel)
    @app.on_event("startup")
    async def startup():
        app.state.router = create_router(settings, db)

    return app


async def async_boot() -> None:
    """Bootstrap complet dans une unique boucle asyncio (uvicorn)."""
    settings = Settings()
    configure_logging(settings)
    log = get_logger()
    log.info("service.starting", version=VERSION)

    mongo_client = create_mongo_client(settings)
    mongo_ok = await check_mongo(mongo_client)
    if not mongo_ok:
        log.error("deps.check", mongo=False, error="MongoDB unreachable")
        raise SystemExit(1)
    log.info("deps.check", mongo=True)

    db = get_database(mongo_client, settings)
    await ensure_indexes(db, settings)
    log.info("db.indexes_created")

    app = create_app(settings, mongo_client)

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.http_port,
        log_level=settings.log_level.lower(),
        log_config=None,
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    finally:
        with suppress(Exception):
            mongo_client.close()


def boot() -> None:
    """Point d'entrée du processus."""
    try:
        asyncio.run(async_boot())
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        sys.exit(code)


if __name__ == "__main__":
    boot()