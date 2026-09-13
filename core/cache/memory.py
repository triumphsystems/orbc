import asyncio
import fnmatch
import logging
import time
from typing import Any

from core.cache.base import BaseCache

logger = logging.getLogger("core.cache.memory")


class InMemoryCache(BaseCache):
    """Thread-safe and async-safe in-memory cache with TTL eviction."""

    def __init__(self, prefix: str = "orb", max_entries: int = 5000):
        super().__init__(prefix=prefix)
        self.max_entries = max_entries
        self._store: dict[str, tuple[Any, float | None]] = {}  # key -> (value, expire_at)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        now = time.time()
        async with self._lock:
            if key in self._store:
                val, expire_at = self._store[key]
                if expire_at is None or now < expire_at:
                    return val
                # Expired
                self._store.pop(key, None)
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expire_at = (time.time() + ttl_seconds) if ttl_seconds is not None else None
        async with self._lock:
            if len(self._store) >= self.max_entries and key not in self._store:
                # Evict oldest 10%
                keys_to_evict = list(self._store.keys())[: max(1, self.max_entries // 10)]
                for k in keys_to_evict:
                    self._store.pop(k, None)
            self._store[key] = (value, expire_at)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            return bool(self._store.pop(key, None))

    async def delete_pattern(self, pattern: str) -> int:
        deleted = 0
        async with self._lock:
            matched_keys = [
                k for k in self._store.keys()
                if fnmatch.fnmatch(k, pattern)
            ]
            for k in matched_keys:
                self._store.pop(k, None)
                deleted += 1
        return deleted

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
