import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from core.config.settings import Settings, get_settings

logger = logging.getLogger("core.pipeline.retrieval.page_cache")


class PageCache(ABC):
    """Abstract interface for provider-agnostic transient page and snapshot caching."""

    prefix: str

    def __init__(self, prefix: str = "orb"):
        self.prefix = prefix.strip(":")

    def get_cache_key(self, url: str) -> str:
        """Returns normalized cache key e.g. orb:cache:page:{sha256_hash}"""
        url_hash = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
        return f"{self.prefix}:cache:page:{url_hash}"

    @abstractmethod
    async def get_page(self, url: str) -> str | None:
        """Retrieves cached page content for a URL, or None if not cached/expired."""
        pass

    @abstractmethod
    async def set_page(self, url: str, content: str, ttl_seconds: int = 3600) -> None:
        """Stores page content in cache with a configurable TTL."""
        pass

    async def get_many(self, urls: list[str]) -> dict[str, str | None]:
        """Retrieves cached content for multiple URLs."""
        results: dict[str, str | None] = {}
        for u in urls:
            results[u] = await self.get_page(u)
        return results

    async def set_many(self, pages: dict[str, str | None], ttl_seconds: int = 3600) -> None:
        """Stores multiple pages in cache."""
        for u, content in pages.items():
            if content:
                await self.set_page(u, content, ttl_seconds=ttl_seconds)


class InMemoryPageCache(PageCache):
    """In-memory page cache with TTL expiration."""

    def __init__(self, prefix: str = "orb"):
        super().__init__(prefix=prefix)
        self._cache: dict[str, tuple[str, float]] = {}  # key -> (content, expire_time)
        self._mutex = asyncio.Lock()

    async def get_page(self, url: str) -> str | None:
        key = self.get_cache_key(url)
        now = time.time()

        async with self._mutex:
            if key in self._cache:
                content, expire_time = self._cache[key]
                if now < expire_time:
                    logger.debug(f"[InMemoryCache HIT] {url}")
                    return content
                # Expired
                self._cache.pop(key, None)
        return None

    async def set_page(self, url: str, content: str, ttl_seconds: int = 3600) -> None:
        if not content:
            return
        key = self.get_cache_key(url)
        now = time.time()

        async with self._mutex:
            self._cache[key] = (content, now + ttl_seconds)
            logger.debug(f"[InMemoryCache SET] {url} (ttl={ttl_seconds}s)")


class RedisPageCache(PageCache):
    """
    Distributed page cache backed by Redis.
    Key format: orb:cache:page:{sha256_hash}
    """

    def __init__(self, broker_url: str = "redis://localhost:6379/0", prefix: str = "orb", redis_client: Any = None):
        super().__init__(prefix=prefix)
        self.broker_url = broker_url
        self._client = redis_client
        self._fallback = InMemoryPageCache(prefix=prefix)

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self.broker_url, decode_responses=True)
            except ImportError:
                return None
            except Exception as err:
                logger.error(f"Failed to connect to Redis for page cache at {self.broker_url}: {err}")
                return None
        return self._client

    async def get_page(self, url: str) -> str | None:
        client = await self._get_client()
        if client is None:
            return await self._fallback.get_page(url)

        key = self.get_cache_key(url)
        try:
            val = await client.get(key)
            if val:
                logger.debug(f"[RedisCache HIT] {url}")
                return val
            return None
        except Exception as err:
            logger.warning(f"Redis page cache get error: {err}. Falling back to in-memory.")
            return await self._fallback.get_page(url)

    async def set_page(self, url: str, content: str, ttl_seconds: int = 3600) -> None:
        if not content:
            return
        client = await self._get_client()
        if client is None:
            await self._fallback.set_page(url, content, ttl_seconds=ttl_seconds)
            return

        key = self.get_cache_key(url)
        try:
            await client.set(key, content, ex=ttl_seconds)
            logger.debug(f"[RedisCache SET] {url} (ttl={ttl_seconds}s)")
        except Exception as err:
            logger.warning(f"Redis page cache set error: {err}")
            await self._fallback.set_page(url, content, ttl_seconds=ttl_seconds)

    async def get_many(self, urls: list[str]) -> dict[str, str | None]:
        client = await self._get_client()
        if client is None or not hasattr(client, "mget"):
            return await super().get_many(urls)

        keys = [self.get_cache_key(u) for u in urls]
        try:
            values = await client.mget(keys)
            return {url: val for url, val in zip(urls, values)}
        except Exception as err:
            logger.warning(f"Redis mget error: {err}")
            return await super().get_many(urls)


class PageCacheFactory:
    """Factory for creating and configuring page caches."""

    @classmethod
    def get_cache(cls, settings: Settings | None = None) -> PageCache:
        cfg = settings or get_settings()
        backend = (cfg.event_broker_backend or "memory").strip().lower()
        prefix = cfg.broker_key_prefix or "orb"

        if backend == "redis":
            return RedisPageCache(broker_url=cfg.broker_url, prefix=prefix)

        return InMemoryPageCache(prefix=prefix)
