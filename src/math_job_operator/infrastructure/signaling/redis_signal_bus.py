"""Redis-backed completion signaling between job coroutines (research.md §2).

Using Redis (rather than an in-process `asyncio.Event`) keeps upstream/dependent job
coordination correct even if the service runs multiple worker processes, consistent with
Constitution Principle V (Statelessness & Distributed State).
"""

import asyncio

import redis.asyncio as redis_asyncio


class RedisSignalBus:
    """Publishes and awaits per-batch, per-job-name completion signals.

    Example:
        >>> bus = RedisSignalBus("redis://localhost:6379/0")  # doctest: +SKIP
        >>> await bus.publish_completion("batch-1", "job_a", "completed")  # doctest: +SKIP
        >>> await bus.wait_for_completion("batch-1", "job_a")  # doctest: +SKIP
        'completed'
    """

    def __init__(self, redis_url: str) -> None:
        self._redis: redis_asyncio.Redis = redis_asyncio.Redis.from_url(redis_url)

    @staticmethod
    def _key(batch_id: str, job_name: str) -> str:
        return f"job-signal:{batch_id}:{job_name}"

    async def publish_completion(self, batch_id: str, job_name: str, status: str) -> None:
        """Record that `job_name` in `batch_id` finished with `status`."""
        await self._redis.set(self._key(batch_id, job_name), status, ex=300)

    async def wait_for_completion(
        self, batch_id: str, job_name: str, *, poll_interval: float = 0.05
    ) -> str:
        """Block (asynchronously) until `job_name` in `batch_id` has a recorded status."""
        key = self._key(batch_id, job_name)
        while True:
            value = await self._redis.get(key)
            if value is not None:
                return value.decode() if isinstance(value, bytes) else str(value)
            await asyncio.sleep(poll_interval)

    async def close(self) -> None:
        """Release the underlying Redis connection."""
        await self._redis.aclose()
