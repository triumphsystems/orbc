import asyncio
import logging
from typing import Any

import httpx

from core.config.settings import get_settings
from core.pipeline.retrieval.direct import DirectHttpRetrieval
from core.pipeline.retrieval.page_cache import PageCache, PageCacheFactory
from core.pipeline.retrieval.rate_limiter import DomainRateLimiter, RateLimiterFactory

logger = logging.getLogger("core.pipeline.retrieval.proxy")


class ProxyRetrieval:
    """Resilient proxy and unlocker-based page retrieval with distributed caching, domain rate limiting, and direct HTTP fallback."""

    cache: PageCache
    rate_limiter: DomainRateLimiter

    def __init__(
        self,
        cache: PageCache | None = None,
        rate_limiter: DomainRateLimiter | None = None,
    ):
        self.settings = get_settings()
        self.direct_fallback = DirectHttpRetrieval()
        self.cache = cache or PageCacheFactory.get_cache()
        self.rate_limiter = rate_limiter or RateLimiterFactory.get_limiter()

    async def retrieve_one(self, url: str, country_code: str | None = None, use_cache: bool = True) -> str | None:
        # 1. Check transient cache
        if use_cache:
            cached = await self.cache.get_page(url)
            if cached is not None:
                return cached

        content: str | None = None

        # 2. Acquire domain concurrency slot before outbound proxy request
        async with self.rate_limiter.limit(url, max_concurrent=4):
            if self.settings.retrieval_api_key and self.settings.retrieval_zone:
                try:
                    headers = {
                        "Authorization": f"Bearer {self.settings.retrieval_api_key}",
                        "Content-Type": "application/json",
                    }

                    payload = {
                        "zone": self.settings.retrieval_zone,
                        "url": url,
                        "format": "raw",
                        "data_format": "markdown",
                    }

                    if country_code:
                        payload["country"] = country_code.lower()

                    request_url = f"{self.settings.retrieval_base_url}/request"

                    async with httpx.AsyncClient(timeout=45.0) as client:
                        resp = await client.post(request_url, headers=headers, json=payload)
                        if resp.status_code == 200 and resp.text:
                            content = resp.text
                except Exception:  # noqa: BLE001
                    pass

            # 3. Fallback to Direct HTTP if proxy failed or unconfigured
            if not content:
                content = await self.direct_fallback.retrieve_one(url, country_code=country_code)

        # 4. Populate cache on success
        if content:
            await self.cache.set_page(url, content, ttl_seconds=3600)

        return content

    async def retrieve_many(
        self, urls: list[str], country_code: str | None = None, concurrency: int = 5, use_cache: bool = True
    ) -> dict[str, str | None]:
        """Concurrent retrieval with transient caching and domain-level rate limiting."""
        results: dict[str, str | None] = {}
        uncached_urls: list[str] = []

        # 1. Check cache in bulk
        if use_cache:
            cached_pages = await self.cache.get_many(urls)
            for u in urls:
                if cached_pages.get(u):
                    results[u] = cached_pages[u]
                else:
                    uncached_urls.append(u)
        else:
            uncached_urls = list(urls)

        if not uncached_urls:
            return results

        # 2. Concurrently fetch uncached URLs
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch(u: str):
            async with semaphore:
                try:
                    content = await self.retrieve_one(u, country_code=country_code, use_cache=False)
                    results[u] = content
                except Exception:  # noqa: BLE001
                    results[u] = None

        await asyncio.gather(*(fetch(u) for u in uncached_urls))
        return results

