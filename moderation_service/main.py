"""Bootstrap du service — version minimale (Tâche 01).

Charge les settings, configure la journalisation, vérifie la dépendance Redis,
monte FastAPI (`/health`). Le WorkerPool est branché en tâche 07/08.
"""

from __future__ import annotations

import sys

import uvicorn
from fastapi import FastAPI

from app.api.health import build_health_router
from app.config.logging import configure_logging, get_logger
from app.config.redis import check_redis, create_redis
from app.config.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Fabrique l'application FastAPI avec la route `/health`."""
    settings = settings or Settings()
    redis_client = create_redis(settings)
    app = FastAPI(title="moderation_service", version="0.1.0")
    app.state.settings = settings
    app.state.redis_client = redis_client
    app.include_router(build_health_router(settings, redis_client))
    return app


def boot() -> None:
    """Point d'entrée du processus : vérifie Redis puis démarre uvicorn."""
    settings = Settings()
    configure_logging(settings)
    log = get_logger()
    log.info("service.starting", version="0.1.0")

    redis_client = create_redis(settings)
    # Dépendance obligatoire : Redis injoignable → arrêt immédiat (rules.md §2).
    from asyncio import run

    if not run(check_redis(redis_client)):
        log.error("deps.check", redis=False, error="Redis unreachable")
        sys.exit(1)
    log.info("deps.check", redis=True)

    app = create_app(settings)
    uvicorn.run(app, host="0.0.0.0", port=settings.http_port)


if __name__ == "__main__":
    boot()
