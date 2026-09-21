"""`DynamicSemaphore` (§9.1) : bornes, waiters, réveil sur `set_capacity`, pas de préemption."""

from __future__ import annotations

import asyncio

import pytest

from app.core.worker_pool import DynamicSemaphore


async def _acquire(sem: DynamicSemaphore, acquired: asyncio.Event) -> None:
    await sem.acquire()
    acquired.set()


@pytest.mark.unit
def test_clamps_initial_and_bounds() -> None:
    sem = DynamicSemaphore(10, max_capacity=4)
    assert sem.capacity == 4
    assert DynamicSemaphore(-2, max_capacity=4).capacity == 0
    assert DynamicSemaphore(2).capacity == 2

    sem.set_capacity(999)
    assert sem.capacity == 4
    sem.set_capacity(-5)
    assert sem.capacity == 0
    sem.set_capacity(3)
    assert sem.capacity == 3


@pytest.mark.unit
async def test_acquire_release_roundtrip() -> None:
    sem = DynamicSemaphore(1, max_capacity=3)
    await sem.acquire()
    assert sem.active == 1 and sem.waiting == 0
    sem.release()
    assert sem.active == 0


@pytest.mark.unit
async def test_blocks_beyond_capacity_and_wakes_on_release() -> None:
    sem = DynamicSemaphore(1, max_capacity=3)
    await sem.acquire()
    acquired = asyncio.Event()
    task = asyncio.create_task(_acquire(sem, acquired))
    await asyncio.sleep(0)
    assert not acquired.is_set()
    assert sem.waiting == 1 and sem.active == 1

    sem.release()
    await asyncio.sleep(0)
    assert acquired.is_set()  # waiter réveillé → acquis
    assert sem.waiting == 0 and sem.active == 1
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.unit
async def test_set_capacity_zero_blocks_new_without_breaking_running() -> None:
    sem = DynamicSemaphore(2, max_capacity=4)
    await sem.acquire()
    await sem.acquire()
    sem.set_capacity(0)

    acquired = asyncio.Event()
    task = asyncio.create_task(_acquire(sem, acquired))
    await asyncio.sleep(0)
    assert sem.waiting == 1  # nouveau acquire bloqué
    assert sem.active == 2   # tâches en cours non interrompues

    sem.release()
    await asyncio.sleep(0)
    assert not acquired.is_set()  # capacité 0 : pas de place
    sem.release()
    await asyncio.sleep(0)
    assert not acquired.is_set() and sem.active == 0

    sem.set_capacity(2)
    await asyncio.sleep(0)
    assert acquired.is_set() and sem.active == 1
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.unit
async def test_reduction_does_not_preempt_active_tasks() -> None:
    sem = DynamicSemaphore(3, max_capacity=3)
    await sem.acquire()
    await sem.acquire()
    await sem.acquire()
    assert sem.active == 3

    sem.set_capacity(1)
    acquired = asyncio.Event()
    task = asyncio.create_task(_acquire(sem, acquired))
    await asyncio.sleep(0)
    assert sem.waiting == 1 and sem.active == 3  # rien n'a été interrompu

    sem.release()  # une tâche en cours termine
    await asyncio.sleep(0)
    assert not acquired.is_set()  # le waiter n'entre pas (active 2 >= capacité 1)
    assert sem.active == 2
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.unit
async def test_set_capacity_increase_wakes_multiple_waiters() -> None:
    sem = DynamicSemaphore(1, max_capacity=10)
    await sem.acquire()
    acquired = [asyncio.Event() for _ in range(3)]
    tasks = [asyncio.create_task(_acquire(sem, ev)) for ev in acquired]
    await asyncio.sleep(0)
    assert sem.waiting == 3

    sem.release()  # 1 place : un seul waiter entre
    await asyncio.sleep(0)
    assert sum(ev.is_set() for ev in acquired) == 1
    assert sem.waiting == 2 and sem.active == 1

    sem.set_capacity(4)  # 3 places de plus → les 2 restants entrent
    await asyncio.sleep(0)
    assert sum(ev.is_set() for ev in acquired) == 3
    assert sem.waiting == 0 and sem.active == 3

    for task in tasks:
        task.cancel()
    await asyncio.gather(*[t for t in tasks], return_exceptions=True)
    sem.release()
    sem.release()
    sem.release()


@pytest.mark.unit
async def test_context_manager() -> None:
    sem = DynamicSemaphore(1, max_capacity=2)
    async with sem:
        assert sem.active == 1
    assert sem.active == 0
