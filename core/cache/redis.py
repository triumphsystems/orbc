import json
import logging
from typing import Any

from core.cache.base import BaseCache
from core.cache.memory import InMemoryCache

logger = logging.getLogger("core.cache.redis")


class RedisCache(BaseCache):
    """Distributed Redis-backed cache with automatic in-memory fallback."""

    def __init__(
        self,
        broker_url: str = "redis://localhost:6379/1",
        prefix: str = "orb",
        redis_client: Any = None,
    ):
        super().__init__(prefix=prefix)
        self.broker_url = broker_url
        self._client = redis_client
        self._fallback = InMemoryCache(prefix=prefix)

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self.broker_url, decode_responses=True)
            except Exception as e:
                logger.debug(f"Redis client initialization failed: {e}. Using in-memory fallback.")
                return None
        return self._client

    async def get(self, key: str) -> Any | None:
        client = await self._get_client()
        if client:
            try:
                raw = await client.get(key)
                if raw is not None:
                    try:
                        return json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        return raw
                return None
            except Exception as e:
                logger.debug(f"Redis GET failed: {e}. Falling back to memory.")
        return await self._fallback.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        client = await self._get_client()
        serialized = json.dumps(value, default=str) if isinstance(value, (dict, list, bool, int, float)) else str(value)
        if client:
            try:
                if ttl_seconds:
                    await client.setex(key, ttl_seconds, serialized)
                else:
                    await client.set(key, serialized)
                return
            except Exception as e:
                logger.debug(f"Redis SET failed: {e}. Falling back to memory.")
        await self._fallback.set(key, value, ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        if client:
            try:
                res = await client.delete(key)
                return res > 0
            except Exception:
                pass
        return await self._fallback.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        client = await self._get_client()
        deleted = 0
        if client:
            try:
                keys = await client.keys(pattern)
                if keys:
                    deleted = await client.delete(*keys)
                return deleted
            except Exception:
                pass
        return await self._fallback.delete_pattern(pattern)

    async def clear(self) -> None:
        client = await self._get_client()
        if client:
            try:
                keys = await client.keys(f"{self.prefix}:*")
                if keys:
                    await client.delete(*keys)
            except Exception:
                pass
        await self._fallback.clear()
