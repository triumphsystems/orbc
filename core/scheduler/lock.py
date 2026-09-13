import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

from core.config.settings import Settings, get_settings

logger = logging.getLogger("core.scheduler.lock")


class DistributedLock(ABC):
    """Abstract interface for provider-agnostic distributed leader election and concurrency locks."""

    prefix: str

    def __init__(self, prefix: str = "orb"):
        self.prefix = prefix.strip(":")

    def get_lock_key(self, name: str) -> str:
        """Returns normalized lock key: e.g. orb:lock:{name}"""
        clean_name = name.strip(":")
        return f"{self.prefix}:lock:{clean_name}"

    @abstractmethod
    async def acquire(self, name: str, timeout_seconds: int = 25) -> bool:
        """Attempts to acquire the named lock. Returns True if successfully acquired, False otherwise."""
        pass

    @abstractmethod
    async def release(self, name: str) -> None:
        """Releases the held lock."""
        pass


class InMemoryLock(DistributedLock):
    """In-memory distributed lock simulator with TTL expiration and asyncio locking."""

    def __init__(self, prefix: str = "orb"):
        super().__init__(prefix=prefix)
        self._locks: dict[str, float] = {}  # key -> expire_timestamp
        self._tokens: dict[str, str] = {}   # key -> owner token
        self._mutex = asyncio.Lock()

    async def acquire(self, name: str, timeout_seconds: int = 25) -> bool:
        key = self.get_lock_key(name)
        now = time.time()

        async with self._mutex:
            # Check if existing lock is expired
            if key in self._locks:
                if now < self._locks[key]:
                    return False  # Still actively held by another process/coroutine
                # Expired, clean up
                self._locks.pop(key, None)
                self._tokens.pop(key, None)

            # Acquire new lease
            self._locks[key] = now + timeout_seconds
            self._tokens[key] = str(uuid.uuid4())
            return True

    async def release(self, name: str) -> None:
        key = self.get_lock_key(name)
        async with self._mutex:
            self._locks.pop(key, None)
            self._tokens.pop(key, None)


class RedisLock(DistributedLock):
    """
    Production Redis distributed lock implementation using atomic SET NX EX.
    Key format: orb:lock:{name}
    """

    def __init__(self, broker_url: str = "redis://localhost:6379/0", prefix: str = "orb", redis_client: Any = None):
        super().__init__(prefix=prefix)
        self.broker_url = broker_url
        self._client = redis_client
        self._owner_tokens: dict[str, str] = {}
        self._fallback = InMemoryLock(prefix=prefix)

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self.broker_url, decode_responses=True)
            except ImportError:
                logger.warning("redis package not installed. Falling back to in-memory lock.")
                return None
            except Exception as err:
                logger.error(f"Failed to connect to Redis for lock at {self.broker_url}: {err}")
                return None
        return self._client

    async def acquire(self, name: str, timeout_seconds: int = 25) -> bool:
        client = await self._get_client()
        if client is None:
            return await self._fallback.acquire(name, timeout_seconds=timeout_seconds)

        key = self.get_lock_key(name)
        token = str(uuid.uuid4())

        try:
            # Atomic SET key token NX EX timeout_seconds
            acquired = await client.set(key, token, nx=True, ex=timeout_seconds)
            if acquired:
                self._owner_tokens[key] = token
                return True
            return False
        except Exception as err:
            logger.warning(f"Redis lock acquire error on {key}: {err}. Falling back to in-memory lock.")
            return await self._fallback.acquire(name, timeout_seconds=timeout_seconds)

    async def release(self, name: str) -> None:
        client = await self._get_client()
        if client is None:
            await self._fallback.release(name)
            return

        key = self.get_lock_key(name)
        token = self._owner_tokens.pop(key, None)
        if not token:
            return

        # Lua script to release lock only if the token matches the owner
        lua_release = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            if hasattr(client, "eval"):
                await client.eval(lua_release, 1, key, token)
            else:
                await client.delete(key)
        except Exception as err:
            logger.warning(f"Redis lock release error on {key}: {err}")


class LockFactory:
    """Factory for creating and configuring distributed locks."""

    @classmethod
    def get_lock(cls, settings: Settings | None = None) -> DistributedLock:
        cfg = settings or get_settings()
        backend = (cfg.event_broker_backend or "memory").strip().lower()
        prefix = cfg.broker_key_prefix or "orb"

        if backend == "redis":
            return RedisLock(broker_url=cfg.broker_url, prefix=prefix)

        return InMemoryLock(prefix=prefix)
