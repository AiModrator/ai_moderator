"""Bootstrap définitif du service (main.md §12).

Séquence de démarrage :
1. `Settings` (`.env.local` prioritaire) puis configuration structlog.
2. Vérification des dépendances : Redis `PING` (échec → log `error` + exit 1),
   `GET {AI_GATEWAY_URL}/health` (échec → log `warning`, on démarre quand même :
   les filtres IA passeront en `UNAVAILABLE` après retries).
3. Chargement des lexiques (`LexiconRepository.load()`), échec → exit 1.
4. FastAPI (uvicorn, `HTTP_PORT`) et `WorkerPool.start()` dans la même boucle
   asyncio ; uvicorn gère les signaux, le pool draine à l'arrêt.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import suppress

import structlog
import uvicorn
from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.health import build_health_router
from app.clients.ai_gateway import AIGatewayClient
from app.config.logging import configure_logging, get_logger
from app.config.redis import check_redis, create_redis
from app.config.settings import Settings
from app.core.filter_factory import FilterFactory
from app.core.pipeline import PipelineBuilder
from app.core.publisher import DecisionPublisher, RetryScheduler, build_queue
from app.core.resource_monitor import ResourceMonitor
from app.core.worker import Worker
from app.core.worker_pool import DynamicSemaphore, WorkerPool
from app.filters.base import BaseFilter
from app.filters.lexicon_repository import LexiconRepository

VERSION = "0.1.0"


def build_gateway(settings: Settings) -> AIGatewayClient:
    """Client AI Gateway (contrat provisoire §5.6) configuré depuis `Settings`."""
    return AIGatewayClient(
        settings.ai_gateway_url,
        api_key=settings.ai_gateway_api_key,
        timeout_sec=settings.ai_request_timeout_sec,
        max_parallel=settings.ai_max_parallel_requests,
    )


def build_lexicon_repository() -> LexiconRepository:
    """Dépôt de lexiques sur les ressources embarquées (`app/resources/lexicons`)."""
    return LexiconRepository()


def build_pool(
    settings: Settings,
    *,
    redis_client: Redis,
    gateway: AIGatewayClient,
    lexicon: LexiconRepository,
    registry: list[type[BaseFilter]] | None = None,
) -> WorkerPool:
    """Assemble le `WorkerPool` de production : files, sémaphore, monitor, filters.

    `registry` explicite en test (le registre global peut être pollué par des
    filtres de test) ; `None` → registre global (production).
    """
    content_queue = build_queue(settings.content_queue_name, settings)
    decision_queue = build_queue(settings.decision_queue_name, settings)
    semaphore = DynamicSemaphore(settings.worker_pool_initial, max_capacity=settings.worker_pool_max)
    monitor = ResourceMonitor(settings, semaphore, purge=lexicon.purge_caches)
    factory = FilterFactory(settings, redis=redis_client, gateway=gateway, lexicon=lexicon)
    builder = PipelineBuilder(registry=registry) if registry is not None else PipelineBuilder()

    def make_worker() -> Worker:
        return Worker(
            settings=settings,
            publisher=DecisionPublisher(decision_queue),
            scheduler=RetryScheduler(
                content_queue,
                base_delay_ms=settings.retry_base_delay_ms,
                max_delay_ms=settings.retry_max_delay_ms,
            ),
            builder=builder,
            factory=factory,
        )

    return WorkerPool(settings, make_worker=make_worker, semaphore=semaphore, monitor=monitor)


def create_app(
    settings: Settings | None = None,
    *,
    redis_client: Redis | None = None,
    pool: WorkerPool | None = None,
    gateway: AIGatewayClient | None = None,
) -> FastAPI:
    """Fabrique l'application FastAPI (`/health` branché sur le pool et la gateway)."""
    settings = settings or Settings()
    redis_client = redis_client or create_redis(settings)
    app = FastAPI(title="moderation_service", version=VERSION)
    app.state.settings = settings
    app.state.redis_client = redis_client
    app.state.pool = pool
    app.state.gateway = gateway
    app.include_router(
        build_health_router(
            settings,
            redis_client,
            pool_stats=pool.stats if pool else None,
            gateway_check=gateway.health if gateway else None,
        )
    )
    return app


def resolve_dependencies(redis_ok: bool, gateway_ok: bool, log: structlog.stdlib.BoundLogger) -> None:
    """Applique la règle §12.2 : Redis KO → `SystemExit(1)` ; gateway KO → warning."""
    if not redis_ok:
        log.error("deps.check", redis=False, error="Redis unreachable")
        raise SystemExit(1)
    if gateway_ok:
        log.info("deps.check", redis=True, aiGateway=True)
    else:
        log.warning("deps.check", redis=True, aiGateway=False)


async def async_boot() -> None:
    """Bootstrap complet dans une unique boucle asyncio (uvicorn + WorkerPool)."""
    settings = Settings()
    configure_logging(settings)
    log = get_logger()
    log.info("service.starting", version=VERSION)

    redis_client = create_redis(settings)
    gateway = build_gateway(settings)
    redis_ok = await check_redis(redis_client)
    gateway_ok = await gateway.health()
    resolve_dependencies(redis_ok, gateway_ok, log)

    lexicon = build_lexicon_repository()
    try:
        lexicon.load()
    except Exception as exc:  # ressources illisibles → service inutilisable
        log.error("deps.lexicons", error=str(exc))
        raise SystemExit(1) from exc
    log.info("deps.lexicons", loaded=True)

    pool = build_pool(settings, redis_client=redis_client, gateway=gateway, lexicon=lexicon)
    app = create_app(settings, redis_client=redis_client, pool=pool, gateway=gateway)

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.http_port,
        log_level=settings.log_level.lower(),
        log_config=None,
    )
    server = uvicorn.Server(config)
    pool_task = asyncio.create_task(pool.start(install_signals=False))
    try:
        await server.serve()
    finally:
        await pool.stop()
        pool_task.cancel()
        with suppress(asyncio.CancelledError):
            await pool_task
        with suppress(Exception):
            await gateway.aclose()
        with suppress(Exception):
            await redis_client.aclose()


def boot() -> None:
    """Point d'entrée du processus : exécute `async_boot` et transmet l'`exit code`."""
    try:
        asyncio.run(async_boot())
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        sys.exit(code)


if __name__ == "__main__":
    boot()
