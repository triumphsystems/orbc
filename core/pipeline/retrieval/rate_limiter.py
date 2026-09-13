import asyncio
import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

from core.config.settings import Settings, get_settings

logger = logging.getLogger("core.pipeline.retrieval.rate_limiter")


class DomainRateLimiter(ABC):
    """Abstract interface for provider-agnostic domain concurrency and rate limiting."""

    prefix: str

    def __init__(self, prefix: str = "orb"):
        self.prefix = prefix.strip(":")

    def get_concurrency_key(self, domain: str) -> str:
        """Returns Redis concurrency key e.g. orb:rate:concurrency:huggingface.co"""
        clean_domain = domain.lower().strip(":")
        return f"{self.prefix}:rate:concurrency:{clean_domain}"

    @abstractmethod
    async def acquire(self, domain: str, max_concurrent: int = 4, timeout: float = 30.0) -> bool:
        """Acquires a concurrency slot for the domain. Blocks up to timeout seconds."""
        pass

    @abstractmethod
    async def release(self, domain: str) -> None:
        """Releases the concurrency slot for the domain."""
        pass

    @asynccontextmanager
    async def limit(self, domain_or_url: str, max_concurrent: int = 4, timeout: float = 30.0):
        """Asynchronous context manager for domain concurrency limiting."""
        domain = self._extract_domain(domain_or_url)
        acquired = await self.acquire(domain, max_concurrent=max_concurrent, timeout=timeout)
        try:
            yield acquired
        finally:
            if acquired:
                await self.release(domain)

    def _extract_domain(self, domain_or_url: str) -> str:
        if "://" in domain_or_url:
            parsed = urlparse(domain_or_url)
            return parsed.netloc.lower() or domain_or_url.lower()
        return domain_or_url.split("/")[0].lower()


class InMemoryDomainRateLimiter(DomainRateLimiter):
    """In-memory domain rate limiter using asyncio.Semaphore per domain."""

    def __init__(self, prefix: str = "orb"):
        super().__init__(prefix=prefix)
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._mutex = asyncio.Lock()

    async def _get_semaphore(self, domain: str, max_concurrent: int) -> asyncio.Semaphore:
        async with self._mutex:
            if domain not in self._semaphores:
                self._semaphores[domain] = asyncio.Semaphore(max_concurrent)
            return self._semaphores[domain]

    async def acquire(self, domain: str, max_concurrent: int = 4, timeout: float = 30.0) -> bool:
        sem = await self._get_semaphore(domain, max_concurrent)
        try:
            await asyncio.wait_for(sem.acquire(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for concurrency slot on domain {domain} (max={max_concurrent})")
            return False

    async def release(self, domain: str) -> None:
        async with self._mutex:
            sem = self._semaphores.get(domain)
        if sem:
            try:
                sem.release()
            except ValueError:
                pass


class RedisDomainRateLimiter(DomainRateLimiter):
    """
    Distributed domain concurrency limiter backed by Redis atomic counter and Lua scripts.
    Key format: orb:rate:concurrency:{domain}
    """

    def __init__(self, broker_url: str = "redis://localhost:6379/0", prefix: str = "orb", redis_client: Any = None):
        super().__init__(prefix=prefix)
        self.broker_url = broker_url
        self._client = redis_client
        self._fallback = InMemoryDomainRateLimiter(prefix=prefix)

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self.broker_url, decode_responses=True)
            except ImportError:
                return None
            except Exception as err:
                logger.error(f"Failed to connect to Redis for rate limiting at {self.broker_url}: {err}")
                return None
        return self._client

    async def acquire(self, domain: str, max_concurrent: int = 4, timeout: float = 30.0) -> bool:
        client = await self._get_client()
        if client is None:
            return await self._fallback.acquire(domain, max_concurrent=max_concurrent, timeout=timeout)

        key = self.get_concurrency_key(domain)
        start_time = time.time()

        # Lua script: if current concurrency < max_concurrent, increment and set TTL 60s
        lua_acquire = """
        local current = tonumber(redis.call("get", KEYS[1]) or "0")
        local max_concurrency = tonumber(ARGV[1])
        if current < max_concurrency then
            local next_val = redis.call("incr", KEYS[1])
            redis.call("expire", KEYS[1], 60)
            return next_val
        else
            return 0
        end
        """

        while time.time() - start_time < timeout:
            try:
                if hasattr(client, "eval"):
                    res = await client.eval(lua_acquire, 1, key, max_concurrent)
                else:
                    res = 1
                if res and int(res) > 0:
                    return True
            except Exception as err:
                logger.warning(f"Redis rate limiter acquire error: {err}. Falling back to in-memory.")
                return await self._fallback.acquire(domain, max_concurrent=max_concurrent, timeout=timeout)

            await asyncio.sleep(0.2)

        logger.warning(f"Redis rate limiter timed out waiting for slot on domain {domain}")
        return False

    async def release(self, domain: str) -> None:
        client = await self._get_client()
        if client is None:
            await self._fallback.release(domain)
            return

        key = self.get_concurrency_key(domain)

        # Lua script: safely decrement without dropping below 0
        lua_release = """
        local current = tonumber(redis.call("get", KEYS[1]) or "0")
        if current > 0 then
            return redis.call("decr", KEYS[1])
        else
            redis.call("del", KEYS[1])
            return 0
        end
        """
        try:
            if hasattr(client, "eval"):
                await client.eval(lua_release, 1, key)
            else:
                await client.delete(key)
        except Exception as err:
            logger.warning(f"Redis rate limiter release error on {key}: {err}")


class RateLimiterFactory:
    """Factory for creating and configuring domain rate limiters."""

    @classmethod
    def get_limiter(cls, settings: Settings | None = None) -> DomainRateLimiter:
        cfg = settings or get_settings()
        cache_backend = (cfg.cache_backend or "").strip().lower()
        broker_backend = (cfg.event_broker_backend or "").strip().lower()
        prefix = cfg.broker_key_prefix or "orb"

        if cache_backend == "redis" or broker_backend == "redis":
            redis_url = cfg.cache_url if cache_backend == "redis" else cfg.broker_url
            return RedisDomainRateLimiter(broker_url=redis_url, prefix=prefix)

        return InMemoryDomainRateLimiter(prefix=prefix)

