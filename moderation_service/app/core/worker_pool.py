"""`WorkerPool` + `DynamicSemaphore` — main.md §9.1/§9.2.

BullMQ préfetche jusqu'à `WORKER_POOL_MAX` jobs (verrous prolongés par bullmq),
mais au plus `semaphore.capacity` s'exécutent : la capacité est pilotée par le
`ResourceMonitor`. `stop()` draine les jobs en cours avant de fermer les
connexions (défaut : `SHUTDOWN_TIMEOUT_SEC`).
"""

from __future__ import annotations

import asyncio
import signal
import time
from collections import deque
from collections.abc import Callable
from contextlib import suppress

import structlog
from bullmq import Worker as BullWorker

from app.config.settings import Settings
from app.core.resource_monitor import ResourceMonitor
from app.core.worker import Worker

logger = structlog.get_logger()

logger = structlog.get_logger()


class DynamicSemaphore:
    """Sémaphore à capacité ajustable (§9.1) : réduction sans interruption."""

    def __init__(self, initial: int = 1, *, max_capacity: int | None = None) -> None:
        high = int(max_capacity) if max_capacity is not None else max(int(initial), 1)
        self._max_capacity = max(high, 0)
        self._capacity = max(0, min(int(initial), self._max_capacity))
        self._active = 0
        self._waiters: deque = deque()

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def active(self) -> int:
        return self._active

    @property
    def waiting(self) -> int:
        return len(self._waiters)

    async def acquire(self) -> None:
        while self._active >= self._capacity:
            future = asyncio.get_running_loop().create_future()
            self._waiters.append(future)
            try:
                await future
            except asyncio.CancelledError:
                if future in self._waiters:
                    self._waiters.remove(future)
                raise
        self._active += 1

    def release(self) -> None:
        self._active = max(0, self._active - 1)
        self._signal()

    def set_capacity(self, n: int) -> None:
        self._capacity = max(0, min(int(n), self._max_capacity))
        self._signal()

    def _signal(self) -> None:
        while self._waiters and self._active < self._capacity:
            self._waiters.popleft().set_result(None)

    async def __aenter__(self) -> DynamicSemaphore:
        await self.acquire()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        self.release()
        return False


class WorkerPool:
    """Boucle worker BullMQ bornée par le sémaphore dynamique (§9.2)."""

    def __init__(
        self,
        settings: Settings,
        *,
        make_worker: Callable[[], Worker],
        semaphore: DynamicSemaphore | None = None,
        monitor: ResourceMonitor | None = None,
        queue_name: str | None = None,
    ) -> None:
        self._settings = settings
        self._make_worker = make_worker
        self._sem = semaphore or DynamicSemaphore(
            settings.worker_pool_initial, max_capacity=settings.worker_pool_max
        )
        self._monitor = monitor or ResourceMonitor(settings, self._sem)
        self._queue_name = queue_name or settings.content_queue_name
        self._paused = False
        connection = {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "password": settings.redis_password or None,
        }
        self._worker = BullWorker(
            self._queue_name,
            self._processor,
            {
                "prefix": settings.test_queue_prefix or "bull",
                "concurrency": settings.worker_pool_max,
                "connection": connection,
            },
        )
        self._monitor_task: asyncio.Task | None = None
        self._started = False
        # BullMQ est « at least once » : sur une relivraison du même jobId
        # (stall/port python), le handler ne doit pas ré-exécuter le travail.
        self._running: set = set()
        self._completed: dict[str, float] = {}
        self._completed_ttl = 300.0

    @property
    def worker(self) -> BullWorker:
        return self._worker

    @property
    def semaphore(self) -> DynamicSemaphore:
        return self._sem

    async def _processor(self, job, token: str | None = None) -> None:
        if job.id in self._running or job.id in self._completed:
            logger.warning("pool.duplicate_dispatch", jobId=job.id)
            return
        self._running.add(job.id)
        try:
            async with self._sem:
                await self._make_worker().process(job)
        finally:
            self._running.discard(job.id)
            self._remember_completed(job.id)

    def _remember_completed(self, job_id: str) -> None:
        now = time.monotonic()
        if len(self._completed) > 4096:
            stale = [jid for jid, ts in self._completed.items() if now - ts >= self._completed_ttl]
            for jid in stale:
                self._completed.pop(jid, None)
        self._completed[job_id] = now

    def stats(self) -> dict:
        paused = bool(self._worker.paused)
        self._paused = paused
        return {
            "capacity": self._sem.capacity,
            "active": self._sem.active,
            "waiting": self._sem.waiting,
            "paused": paused,
            "cpu": self._monitor.last_cpu,
            "ram": self._monitor.last_ram,
            "scale_events": self._monitor.scale_events,
        }

    async def start(self) -> None:
        """Lance le monitor et le worker ; répond aux signaux d'arrêt."""
        loop = asyncio.get_running_loop()
        self._monitor_task = asyncio.create_task(self._monitor.run())
        self._install_signal_handlers(loop)
        self._started = True
        try:
            await self._worker.run()
        finally:
            self._remove_signal_handlers(loop)
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._monitor_task

    def _install_signal_handlers(self, loop) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda s=sig: loop.create_task(self.stop()))
            except (NotImplementedError, RuntimeError, ValueError):
                pass

    def _remove_signal_handlers(self, loop) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.remove_signal_handler(sig)
            except (NotImplementedError, RuntimeError, ValueError):
                pass

    async def stop(self) -> None:
        """Drain gracieux des jobs en cours (≤ `SHUTDOWN_TIMEOUT_SEC`) puis fermeture."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._monitor_task
        if self._started and not self._worker.closed:
            try:
                await asyncio.wait_for(self._worker.close(force=False), timeout=max(self._settings.shutdown_timeout_sec, 0.1))
            except TimeoutError:
                if not self._worker.closed:
                    with suppress(Exception):
                        await self._worker.close(force=True)


__all__ = ["DynamicSemaphore", "WorkerPool"]
