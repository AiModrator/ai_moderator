"""`ResourceMonitor` (§9.3) : toutes les branches de décision + cooldown (provider factice)."""

from __future__ import annotations

import asyncio

import pytest

from app.config.settings import Settings
from app.core.resource_monitor import (
    BACKPRESSURE_OFF,
    BACKPRESSURE_ON,
    NEUTRAL,
    SCALE_DOWN,
    SCALE_UP,
    ResourceMonitor,
)


def make_settings(**overrides) -> Settings:
    base = dict(
        test_queue_prefix="test",
        log_format="console",
        worker_pool_min=2,
        worker_pool_initial=4,
        worker_pool_max=32,
        scale_step=2,
        scale_cooldown_sec=10,
        cpu_low_pct=65,
        cpu_high_pct=85,
        ram_low_pct=70,
        ram_high_pct=80,
        ram_critical_pct=90,
    )
    base.update(overrides)
    return Settings(**base)


class FakeSemaphore:
    def __init__(self, capacity: int, *, waiting: int = 0) -> None:
        self._capacity = capacity
        self._waiting = waiting
        self.calls: list[int] = []

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def waiting(self) -> int:
        return self._waiting

    def set_capacity(self, n: int) -> None:
        self._capacity = n
        self.calls.append(n)


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class Metrics:
    def __init__(self, cpu: float = 10.0, ram: float = 10.0) -> None:
        self.cpu = cpu
        self.ram = ram

    def cpu_percent(self) -> float:
        return self.cpu

    def ram_percent(self) -> float:
        return self.ram


def make_monitor(sem: FakeSemaphore, *, cpu: float = 10.0, ram: float = 10.0, metrics=None, **overrides):
    settings = make_settings(**overrides)
    purges: list[str] = []
    clock = FakeClock()

    def purge() -> None:
        purges.append("purge")

    provider = metrics if metrics is not None else Metrics(cpu=cpu, ram=ram)
    monitor = ResourceMonitor(settings, sem, provider, purge=purge, clock=clock)
    return monitor, sem, purges, clock


@pytest.mark.unit
def test_ram_critical_triggers_backpressure_and_purge() -> None:
    monitor, sem, purges, _ = make_monitor(FakeSemaphore(6, waiting=2), cpu=10, ram=95)
    action = monitor.tick(10, 95)
    assert action == BACKPRESSURE_ON
    assert sem.capacity == 0 and sem.calls == [0]
    assert purges == ["purge"]
    assert monitor.backpressure is True
    assert monitor.scale_events == 1

    # même échantillon : pas de nouveau changement de capacité
    assert monitor.tick(10, 95) == BACKPRESSURE_ON and sem.calls == [0]
    assert monitor.scale_events == 1


@pytest.mark.unit
async def test_backpressure_off_restores_min_then_scale_up() -> None:
    monitor, sem, _, clock = make_monitor(FakeSemaphore(0, waiting=2), cpu=10, ram=95)
    monitor.tick(95, 95)  # ON → 0
    assert monitor.tick(10, 40) == BACKPRESSURE_OFF
    assert sem.capacity == 2  # WORKER_POOL_MIN
    assert monitor.backpressure is False
    assert monitor.scale_events == 2
    # hors backpressure, CPU/RAM bas + waiting>0 → scale up immédiat (pas de cooldown après OFF)
    assert monitor.tick(10, 40) == SCALE_UP
    assert sem.capacity == 4
    clock.now += 10
    assert monitor.tick(10, 40) == SCALE_UP
    assert sem.capacity == 6


@pytest.mark.unit
def test_cpu_high_scales_down() -> None:
    monitor, sem, _, _ = make_monitor(FakeSemaphore(6))
    assert monitor.tick(90, 40) == SCALE_DOWN
    assert sem.capacity == 4
    # cooldown : pas de second changement immédiat
    assert monitor.tick(90, 40) == NEUTRAL
    assert sem.capacity == 4
    assert monitor.scale_events == 1


@pytest.mark.unit
def test_scale_down_respects_cooldown_then_min() -> None:
    monitor, sem, _, clock = make_monitor(FakeSemaphore(4))
    assert monitor.tick(90, 40) == SCALE_DOWN
    assert sem.capacity == 2  # MIN atteint
    clock.now += 10
    assert monitor.tick(90, 40) == NEUTRAL  # déjà à MIN : pas de changement
    assert sem.capacity == 2


@pytest.mark.unit
def test_ram_high_alone_scales_down() -> None:
    monitor, sem, _, _ = make_monitor(FakeSemaphore(6))
    assert monitor.tick(cpu=10, ram=84) == SCALE_DOWN
    assert sem.capacity == 4


@pytest.mark.unit
def test_scale_up_requires_waiting_and_cooldown() -> None:
    monitor, sem, _, clock = make_monitor(FakeSemaphore(2))
    # pas de demande → neutre malgré CPU/RAM bas
    assert monitor.tick(10, 10) == NEUTRAL
    assert sem.capacity == 2

    sem._waiting = 3
    assert monitor.tick(10, 10) == SCALE_UP
    assert sem.capacity == 4
    assert monitor.tick(10, 10) == NEUTRAL  # cooldown
    clock.now += 10
    assert monitor.tick(10, 10) == SCALE_UP
    assert sem.capacity == 6


@pytest.mark.unit
def test_neutral_zone_no_oscillation() -> None:
    monitor, sem, _, _ = make_monitor(FakeSemaphore(4, waiting=3))
    # 70 <= ram=75 < 80 : ni high ni low pour appeler scale_up
    assert monitor.tick(cpu=70, ram=75) == NEUTRAL
    assert sem.capacity == 4
    assert monitor.scale_events == 0


@pytest.mark.unit
def test_backpressure_bypasses_cooldown() -> None:
    # cooldown actif (échelle venant de bouger) mais RAM critique → ON immédiat
    monitor, sem, _, clock = make_monitor(FakeSemaphore(6))
    assert monitor.tick(90, 40) == SCALE_DOWN  # déclenche le cooldown
    clock.now += 2  # < cooldown
    assert monitor.tick(cpu=10, ram=95) == BACKPRESSURE_ON  # immédiat quand même
    assert sem.capacity == 0


@pytest.mark.unit
async def test_run_loop_calls_tick_with_provider_metrics() -> None:
    metrics = Metrics(cpu=99, ram=99)
    monitor, sem, purges, _ = make_monitor(
        FakeSemaphore(4), metrics=metrics, monitor_interval_sec=0.1
    )
    task = asyncio.create_task(monitor.run())
    try:
        await asyncio.sleep(0.25)
        assert sem.calls == [0]  # backpressure déclenché par la boucle
        assert purges == ["purge"]
    finally:
        task.cancel()
