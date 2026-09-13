import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from core.config.settings import Settings, get_settings

logger = logging.getLogger("core.agent.baseline_cache")


class BaselineCache(ABC):
    """Abstract interface for sub-millisecond historical metric baseline caching for condition alerting."""

    prefix: str

    def __init__(self, prefix: str = "orb"):
        self.prefix = prefix.strip(":")

    def get_baseline_key(self, automation_id: str) -> str:
        """Returns normalized baseline key e.g. orb:baseline:{automation_id}"""
        return f"{self.prefix}:baseline:{automation_id}"

    @abstractmethod
    async def get_baseline(self, automation_id: str) -> dict[str, float] | None:
        """Retrieves cached baseline metrics for an automation, or None if not cached."""
        pass

    @abstractmethod
    async def set_baseline(self, automation_id: str, metrics: dict[str, float], ttl_seconds: int = 2592000) -> None:
        """Stores baseline metrics in cache with a 30-day default TTL."""
        pass

    async def update_from_records(
        self, automation_id: str, records: list[dict[str, Any]], ttl_seconds: int = 2592000
    ) -> dict[str, float]:
        """Extracts primary numeric stats (min, max, avg) across records and updates the baseline cache."""
        metrics: dict[str, float] = {}
        numeric_values_by_field: dict[str, list[float]] = {}

        for r in records:
            if not isinstance(r, dict):
                continue
            data = r.get("data")
            if not isinstance(data, dict):
                data = r if not any(k in r for k in ("url", "extracted", "notes", "anomalies")) else {}
            for k, v in data.items():
                if v is not None and not isinstance(v, bool):
                    try:
                        numeric_values_by_field.setdefault(k, []).append(float(v))
                    except (ValueError, TypeError):
                        pass

        for field_name, vals in numeric_values_by_field.items():
            if vals:
                metrics[f"{field_name}_min"] = min(vals)
                metrics[f"{field_name}_max"] = max(vals)
                metrics[f"{field_name}_avg"] = sum(vals) / len(vals)
                metrics[f"{field_name}_count"] = float(len(vals))

        if metrics:
            await self.set_baseline(automation_id, metrics, ttl_seconds=ttl_seconds)

        return metrics


class InMemoryBaselineCache(BaselineCache):
    """In-memory metric baseline cache with TTL expiration."""

    def __init__(self, prefix: str = "orb"):
        super().__init__(prefix=prefix)
        self._cache: dict[str, tuple[dict[str, float], float]] = {}  # key -> (metrics, expire_time)
        self._mutex = asyncio.Lock()

    async def get_baseline(self, automation_id: str) -> dict[str, float] | None:
        key = self.get_baseline_key(automation_id)
        now = time.time()

        async with self._mutex:
            if key in self._cache:
                metrics, expire_time = self._cache[key]
                if now < expire_time:
                    logger.debug(f"[InMemoryBaseline HIT] {automation_id}")
                    return dict(metrics)
                # Expired
                self._cache.pop(key, None)
        return None

    async def set_baseline(self, automation_id: str, metrics: dict[str, float], ttl_seconds: int = 2592000) -> None:
        if not metrics:
            return
        key = self.get_baseline_key(automation_id)
        now = time.time()

        async with self._mutex:
            self._cache[key] = (dict(metrics), now + ttl_seconds)
            logger.debug(f"[InMemoryBaseline SET] {automation_id} ({len(metrics)} metrics, ttl={ttl_seconds}s)")


class RedisBaselineCache(BaselineCache):
    """
    Distributed metric baseline cache backed by Redis Hashes.
    Key format: orb:baseline:{automation_id}
    """

    def __init__(self, broker_url: str = "redis://localhost:6379/0", prefix: str = "orb", redis_client: Any = None):
        super().__init__(prefix=prefix)
        self.broker_url = broker_url
        self._client = redis_client
        self._fallback = InMemoryBaselineCache(prefix=prefix)

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self.broker_url, decode_responses=True)
            except ImportError:
                return None
            except Exception as err:
                logger.error(f"Failed to connect to Redis for baseline cache at {self.broker_url}: {err}")
                return None
        return self._client

    async def get_baseline(self, automation_id: str) -> dict[str, float] | None:
        client = await self._get_client()
        if client is None:
            return await self._fallback.get_baseline(automation_id)

        key = self.get_baseline_key(automation_id)
        try:
            raw_hash = await client.hgetall(key)
            if raw_hash:
                logger.debug(f"[RedisBaseline HIT] {automation_id}")
                return {k: float(v) for k, v in raw_hash.items()}
            return None
        except Exception as err:
            logger.warning(f"Redis baseline get error on {key}: {err}. Falling back to in-memory.")
            return await self._fallback.get_baseline(automation_id)

    async def set_baseline(self, automation_id: str, metrics: dict[str, float], ttl_seconds: int = 2592000) -> None:
        if not metrics:
            return
        client = await self._get_client()
        if client is None:
            await self._fallback.set_baseline(automation_id, metrics, ttl_seconds=ttl_seconds)
            return

        key = self.get_baseline_key(automation_id)
        string_hash = {k: str(v) for k, v in metrics.items()}

        try:
            await client.hset(key, mapping=string_hash)
            await client.expire(key, ttl_seconds)
            logger.debug(f"[RedisBaseline SET] {automation_id} (ttl={ttl_seconds}s)")
        except Exception as err:
            logger.warning(f"Redis baseline set error on {key}: {err}")
            await self._fallback.set_baseline(automation_id, metrics, ttl_seconds=ttl_seconds)


class BaselineCacheFactory:
    """Factory for creating and configuring baseline caches."""

    @classmethod
    def get_cache(cls, settings: Settings | None = None) -> BaselineCache:
        cfg = settings or get_settings()
        backend = (cfg.event_broker_backend or "memory").strip().lower()
        prefix = cfg.broker_key_prefix or "orb"

        if backend == "redis":
            return RedisBaselineCache(broker_url=cfg.broker_url, prefix=prefix)

        return InMemoryBaselineCache(prefix=prefix)
