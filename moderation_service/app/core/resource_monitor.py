"""Boucle d'auto-scaling `ResourceMonitor` — main.md §9.3.

Décision **pure** (injectable : métriques factices, horloge factice) ; chaque
tick pilote la capacité du sémaphore via callback et journalise les événements
`pool.*` (§10). Le backpressure critique est immédiat (garde de cooldown levée),
les changements d'échelle respectent `SCALE_COOLDOWN_SEC`.
"""

from __future__ import annotations

import asyncio
import time
from typing import Protocol

import structlog

from app.config.settings import Settings

logger = structlog.get_logger()


class MetricsProvider(Protocol):
    def cpu_percent(self) -> float: ...
    def ram_percent(self) -> float: ...


class ScaleTarget(Protocol):
    @property
    def capacity(self) -> int: ...
    @property
    def waiting(self) -> int: ...
    def set_capacity(self, n: int) -> None: ...


class PsutilMetrics:
    """Métriques système réelles (psutil)."""

    def cpu_percent(self) -> float:
        import psutil

        return float(psutil.cpu_percent(interval=None))

    def ram_percent(self) -> float:
        import psutil

        return float(psutil.virtual_memory().percent)


BACKPRESSURE_ON = "backpressure_on"
BACKPRESSURE_OFF = "backpressure_off"
SCALE_UP = "scale_up"
SCALE_DOWN = "scale_down"
NEUTRAL = "neutral"


class ResourceMonitor:
    """Décide la capacité cible du sémaphore à partir de CPU/RAM (§9.3)."""

    def __init__(
        self,
        settings: Settings,
        target: ScaleTarget,
        metrics: MetricsProvider | None = None,
        *,
        purge: object | None = None,
        clock: object | None = None,
    ) -> None:
        self._settings = settings
        self._target = target
        self._metrics = metrics if metrics is not None else PsutilMetrics()
        self._purge = purge if purge is not None else _noop
        self._clock = clock if clock is not None else time.monotonic
        self._backpressure = False
        self._last_scale_at: float | None = None
        self._scale_events = 0
        self._last_cpu: float | None = None
        self._last_ram: float | None = None

    @property
    def backpressure(self) -> bool:
        return self._backpressure

    @property
    def scale_events(self) -> int:
        return self._scale_events

    @property
    def last_cpu(self) -> float | None:
        return self._last_cpu

    @property
    def last_ram(self) -> float | None:
        return self._last_ram

    async def run(self) -> None:
        """Boucle : `MONITOR_INTERVAL_SEC` entre deux échantillons."""
        while True:
            await asyncio.sleep(max(self._settings.monitor_interval_sec, 0.1))
            self.tick(self._metrics.cpu_percent(), self._metrics.ram_percent())

    def tick(self, cpu: float, ram: float) -> str:
        """Un échantillon → décision appliquée au sémaphore ; retourne l'action."""
        s = self._settings
        now = self._clock()
        self._last_cpu = cpu
        self._last_ram = ram
        action = self._decide(cpu, ram, now)
        if action == BACKPRESSURE_ON and not self._backpressure:
            self._backpressure = True
            self._scale_events += 1
            self._set_capacity(0)
            self._purge()
            logger.warning(
                "pool.backpressure_on", cpu=cpu, ram=ram, from_capacity=self._target.capacity, to=0
            )
        elif action == BACKPRESSURE_ON and self._backpressure:
            pass  # maintiens le backpressure ; aucun changement de capacité
        elif action == BACKPRESSURE_OFF and self._backpressure:
            self._backpressure = False
            self._scale_events += 1
            self._set_capacity(s.worker_pool_min)
            logger.info(
                "pool.backpressure_off",
                cpu=cpu,
                ram=ram,
                from_capacity=0,
                to=s.worker_pool_min,
            )
        elif action in (SCALE_UP, SCALE_DOWN):
            self._apply_scale(action, cpu, ram, now)
        else:
            logger.debug(
                "monitor.sample",
                cpu=cpu,
                ram=ram,
                capacity=self._target.capacity,
                active=_safe_active(self._target),
                waiting=self._target.waiting,
            )
        return action

    def _decide(self, cpu: float, ram: float, now: float) -> str:
        s = self._settings
        if ram >= s.ram_critical_pct:
            return BACKPRESSURE_ON
        if self._backpressure:
            return BACKPRESSURE_OFF
        if cpu > s.cpu_high_pct or ram > s.ram_high_pct:
            if self._target.capacity <= s.worker_pool_min:
                return NEUTRAL  # déjà au plancher
            if self._cooled_down(now):
                return SCALE_DOWN
            return NEUTRAL
        if cpu < s.cpu_low_pct and ram < s.ram_low_pct and self._target.waiting > 0:
            if self._target.capacity >= s.worker_pool_max:
                return NEUTRAL  # déjà au plafond
            if self._cooled_down(now):
                return SCALE_UP
            return NEUTRAL
        return NEUTRAL

    def _apply_scale(self, action: str, cpu: float, ram: float, now: float) -> None:
        s = self._settings
        old = self._target.capacity
        if action == SCALE_UP:
            target = min(s.worker_pool_max, old + s.scale_step)
            if target <= old:
                return
            self._scale_events += 1
            self._last_scale_at = now
            self._target.set_capacity(target)
            logger.info("pool.scale_up", cpu=cpu, ram=ram, from_capacity=old, to=target)
        else:
            target = max(s.worker_pool_min, old - s.scale_step)
            if target >= old:
                return
            self._scale_events += 1
            self._last_scale_at = now
            self._target.set_capacity(target)
            logger.info("pool.scale_down", cpu=cpu, ram=ram, from_capacity=old, to=target)

    def _cooled_down(self, now: float) -> bool:
        if self._last_scale_at is None:
            return True
        return now - self._last_scale_at >= self._settings.scale_cooldown_sec

    def _set_capacity(self, n: int) -> None:
        # Backpressure (on/off) : immédiat, hors cooldown (§9.3).
        self._target.set_capacity(n)


def _noop() -> None:
    return None


def _safe_active(target: ScaleTarget) -> int:
    active = getattr(target, "active", None)
    return int(active) if active is not None else 0


__all__ = [
    "MetricsProvider",
    "ScaleTarget",
    "PsutilMetrics",
    "ResourceMonitor",
    "BACKPRESSURE_ON",
    "BACKPRESSURE_OFF",
    "SCALE_UP",
    "SCALE_DOWN",
    "NEUTRAL",
]
