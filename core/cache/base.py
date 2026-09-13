import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class BaseCache(ABC):
    """Abstract interface for domain and pipeline caching backends."""

    prefix: str

    def __init__(self, prefix: str = "orb"):
        self.prefix = prefix.strip(":")

    def build_key(self, namespace: str, key_or_data: str | dict | list) -> str:
        """Constructs a normalized, collision-safe cache key."""
        if isinstance(key_or_data, (dict, list)):
            serialized = json.dumps(key_or_data, sort_keys=True, default=str)
            raw_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        else:
            raw_str = str(key_or_data).strip()
            if len(raw_str) > 64 or " " in raw_str or "\n" in raw_str:
                raw_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
            else:
                raw_hash = raw_str
        return f"{self.prefix}:{namespace}:{raw_hash}"

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Retrieves a cached item by exact key, or None if expired/missing."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Sets a value in cache with optional TTL in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Deletes a single key from cache. Returns True if deleted."""
        pass

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """Deletes all keys matching a glob pattern (e.g. 'orb:warehouse:auto-123:*'). Returns count deleted."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Flushes the entire cache namespace."""
        pass

    async def get_or_set(
        self,
        key: str,
        factory_fn: Callable[[], Any],
        ttl_seconds: int | None = None,
    ) -> Any:
        """Gets value from cache, or executes async/sync factory and caches result."""
        cached = await self.get(key)
        if cached is not None:
            return cached

        val = factory_fn()
        if hasattr(val, "__await__"):
            val = await val

        if val is not None:
            await self.set(key, val, ttl_seconds=ttl_seconds)
        return val
