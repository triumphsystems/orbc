import functools
import logging
from typing import Any, Callable

from core.cache.base import BaseCache
from core.cache.memory import InMemoryCache
from core.cache.redis import RedisCache
from core.config.settings import get_settings

logger = logging.getLogger("core.cache.service")


class CacheService:
    """Unified caching service and invalidation dispatcher for Orbit."""

    backend: BaseCache

    def __init__(self, backend: BaseCache | None = None):
        if backend:
            self.backend = backend
        else:
            s = get_settings()
            backend_type = getattr(s, "cache_backend", "memory").lower()
            prefix = getattr(s, "broker_key_prefix", "orb")
            cache_url = getattr(s, "cache_url", "redis://localhost:6379/1")

            if backend_type == "redis":
                self.backend = RedisCache(broker_url=cache_url, prefix=prefix)
            else:
                self.backend = InMemoryCache(prefix=prefix)

    def key_for_dossier(self, run_id: str) -> str:
        return self.backend.build_key("dossier", run_id)

    def key_for_probe(self, adapter_id: str, config: dict) -> str:
        return self.backend.build_key(f"probe:{adapter_id}", config)

    def key_for_plan(self, normalized_goal: str) -> str:
        return self.backend.build_key("plan", normalized_goal)

    def key_for_warehouse(self, automation_id: str, query_params: dict | str = "") -> str:
        return self.backend.build_key(f"warehouse:{automation_id}", query_params)

    async def get(self, key: str) -> Any | None:
        return await self.backend.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        await self.backend.set(key, value, ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> bool:
        return await self.backend.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        return await self.backend.delete_pattern(pattern)

    async def clear(self) -> None:
        await self.backend.clear()

    async def get_or_set(
        self,
        key: str,
        factory_fn: Callable[[], Any],
        ttl_seconds: int | None = None,
    ) -> Any:
        return await self.backend.get_or_set(key, factory_fn, ttl_seconds=ttl_seconds)

    async def invalidate_automation(self, automation_id: str) -> int:
        """Invalidates all cached entries for a given automation (warehouse queries, plans)."""
        pattern = f"{self.backend.prefix}:warehouse:{automation_id}:*"
        count = await self.backend.delete_pattern(pattern)
        logger.info(f"Invalidated {count} cache key(s) for automation {automation_id}")
        return count

    async def invalidate_all_probes(self) -> int:
        pattern = f"{self.backend.prefix}:probe:*"
        return await self.backend.delete_pattern(pattern)


cache_service = CacheService()
