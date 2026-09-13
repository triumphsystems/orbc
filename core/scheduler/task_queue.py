import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

from core.config.settings import Settings, get_settings

logger = logging.getLogger("core.scheduler.task_queue")


class TaskQueue(ABC):
    """Abstract interface for provider-agnostic asynchronous mission task queueing."""

    prefix: str

    def __init__(self, prefix: str = "orb"):
        self.prefix = prefix.strip(":")

    def get_pending_queue_key(self) -> str:
        """Returns pending missions list key: e.g. orb:queue:missions:pending"""
        return f"{self.prefix}:queue:missions:pending"

    def get_active_queue_key(self) -> str:
        """Returns processing lease list key: e.g. orb:queue:missions:active"""
        return f"{self.prefix}:queue:missions:active"

    @abstractmethod
    async def enqueue(self, payload: dict[str, Any]) -> str:
        """Enqueues a task payload. Returns generated task_id."""
        pass

    @abstractmethod
    async def dequeue(self, timeout_seconds: int = 2) -> dict[str, Any] | None:
        """Pulls the next available task from the queue."""
        pass

    @abstractmethod
    async def ack(self, task_id: str) -> None:
        """Acknowledges successful processing and cleans up active lease."""
        pass

    @abstractmethod
    async def get_pending_count(self) -> int:
        """Returns number of pending tasks in queue."""
        pass


class InMemoryTaskQueue(TaskQueue):
    """In-memory async task queue using asyncio.Queue."""

    def __init__(self, prefix: str = "orb"):
        super().__init__(prefix=prefix)
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._active: dict[str, dict[str, Any]] = {}
        self._mutex = asyncio.Lock()

    async def enqueue(self, payload: dict[str, Any]) -> str:
        task_id = payload.get("task_id") or str(uuid.uuid4())
        task_item = {**payload, "task_id": task_id, "enqueued_at": time.time()}
        await self._queue.put(task_item)
        logger.debug(f"[InMemoryQueue ENQUEUE] Task {task_id}")
        return task_id

    async def dequeue(self, timeout_seconds: int = 2) -> dict[str, Any] | None:
        try:
            task = await asyncio.wait_for(self._queue.get(), timeout=timeout_seconds)
            task_id = task["task_id"]
            async with self._mutex:
                self._active[task_id] = task
            logger.debug(f"[InMemoryQueue DEQUEUE] Task {task_id}")
            return task
        except asyncio.TimeoutError:
            return None

    async def ack(self, task_id: str) -> None:
        async with self._mutex:
            self._active.pop(task_id, None)
        logger.debug(f"[InMemoryQueue ACK] Task {task_id}")

    async def get_pending_count(self) -> int:
        return self._queue.qsize()


class RedisTaskQueue(TaskQueue):
    """
    Distributed mission task queue backed by Redis List primitives (LPUSH / BRPOP).
    Keys format: orb:queue:missions:pending, orb:queue:missions:active
    """

    def __init__(self, broker_url: str = "redis://localhost:6379/0", prefix: str = "orb", redis_client: Any = None):
        super().__init__(prefix=prefix)
        self.broker_url = broker_url
        self._client = redis_client
        self._fallback = InMemoryTaskQueue(prefix=prefix)

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self.broker_url, decode_responses=True)
            except ImportError:
                return None
            except Exception as err:
                logger.error(f"Failed to connect to Redis for task queue at {self.broker_url}: {err}")
                return None
        return self._client

    async def enqueue(self, payload: dict[str, Any]) -> str:
        client = await self._get_client()
        if client is None:
            return await self._fallback.enqueue(payload)

        task_id = payload.get("task_id") or str(uuid.uuid4())
        task_item = {**payload, "task_id": task_id, "enqueued_at": time.time()}
        serialized = json.dumps(task_item)

        pending_key = self.get_pending_queue_key()
        try:
            await client.lpush(pending_key, serialized)
            logger.debug(f"[RedisQueue ENQUEUE] Task {task_id} to {pending_key}")
            return task_id
        except Exception as err:
            logger.warning(f"Redis enqueue error on {pending_key}: {err}. Falling back to in-memory.")
            return await self._fallback.enqueue(payload)

    async def dequeue(self, timeout_seconds: int = 2) -> dict[str, Any] | None:
        client = await self._get_client()
        if client is None:
            return await self._fallback.dequeue(timeout_seconds=timeout_seconds)

        pending_key = self.get_pending_queue_key()
        try:
            # BRPOP blocks up to timeout_seconds
            res = await client.brpop(pending_key, timeout=timeout_seconds)
            if res:
                _, raw_task = res
                task_item = json.loads(raw_task)
                logger.debug(f"[RedisQueue DEQUEUE] Task {task_item.get('task_id')}")
                return task_item
            return None
        except Exception as err:
            logger.warning(f"Redis dequeue error on {pending_key}: {err}. Falling back to in-memory.")
            return await self._fallback.dequeue(timeout_seconds=timeout_seconds)

    async def ack(self, task_id: str) -> None:
        # In simple LPUSH/BRPOP queue, pulling pops the task.
        logger.debug(f"[RedisQueue ACK] Task {task_id}")

    async def get_pending_count(self) -> int:
        client = await self._get_client()
        if client is None:
            return await self._fallback.get_pending_count()

        pending_key = self.get_pending_queue_key()
        try:
            return int(await client.llen(pending_key))
        except Exception:
            return 0


class TaskQueueFactory:
    """Factory for creating and configuring task queues."""

    @classmethod
    def get_queue(cls, settings: Settings | None = None) -> TaskQueue:
        cfg = settings or get_settings()
        backend = (cfg.event_broker_backend or "memory").strip().lower()
        prefix = cfg.broker_key_prefix or "orb"

        if backend == "redis":
            return RedisTaskQueue(broker_url=cfg.broker_url, prefix=prefix)

        return InMemoryTaskQueue(prefix=prefix)
