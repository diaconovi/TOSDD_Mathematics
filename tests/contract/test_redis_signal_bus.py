"""Contract tests for RedisSignalBus against a real Redis instance."""

import asyncio

import pytest

from math_job_operator.config import Settings
from math_job_operator.infrastructure.signaling.redis_signal_bus import RedisSignalBus


@pytest.fixture
async def bus(settings: Settings, redis_client: object) -> RedisSignalBus:
    # `redis_client` fixture flushes the test Redis DB before/after this test.
    instance = RedisSignalBus(settings.REDIS_URL)
    yield instance
    await instance.close()


async def test_wait_for_completion_returns_after_publish(bus: RedisSignalBus) -> None:
    async def publisher() -> None:
        await asyncio.sleep(0.1)
        await bus.publish_completion("batch-1", "job_a", "completed")

    waiter = asyncio.create_task(bus.wait_for_completion("batch-1", "job_a"))
    await publisher()

    assert await waiter == "completed"


async def test_wait_for_completion_returns_immediately_if_already_published(
    bus: RedisSignalBus,
) -> None:
    await bus.publish_completion("batch-2", "job_b", "error")

    result = await asyncio.wait_for(bus.wait_for_completion("batch-2", "job_b"), timeout=1.0)

    assert result == "error"


async def test_different_batches_do_not_collide(bus: RedisSignalBus) -> None:
    await bus.publish_completion("batch-3", "job_x", "completed")

    with pytest.raises(TimeoutError):
        await asyncio.wait_for(bus.wait_for_completion("batch-4", "job_x"), timeout=0.3)
