import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config.settings import Settings
from core.pipeline.retrieval.page_cache import (
    InMemoryPageCache,
    PageCacheFactory,
    RedisPageCache,
)
from core.pipeline.retrieval.proxy import ProxyRetrieval
from core.pipeline.retrieval.rate_limiter import (
    InMemoryDomainRateLimiter,
    RateLimiterFactory,
    RedisDomainRateLimiter,
)


@pytest.mark.asyncio
async def test_in_memory_domain_rate_limiter():
    limiter = InMemoryDomainRateLimiter(prefix="orb")
    assert limiter.get_concurrency_key("huggingface.co") == "orb:rate:concurrency:huggingface.co"

    # Acquire up to limit
    acq1 = await limiter.acquire("huggingface.co", max_concurrent=2, timeout=2.0)
    acq2 = await limiter.acquire("huggingface.co", max_concurrent=2, timeout=2.0)
    assert acq1 is True
    assert acq2 is True

    # Third acquire should timeout because max_concurrent=2
    acq3 = await limiter.acquire("huggingface.co", max_concurrent=2, timeout=0.1)
    assert acq3 is False

    # Release one slot
    await limiter.release("huggingface.co")

    # Now acquire should succeed
    acq4 = await limiter.acquire("huggingface.co", max_concurrent=2, timeout=1.0)
    assert acq4 is True
    await limiter.release("huggingface.co")
    await limiter.release("huggingface.co")


@pytest.mark.asyncio
async def test_redis_domain_rate_limiter():
    mock_redis = MagicMock()
    mock_redis.eval = AsyncMock(side_effect=[1, 2, 0])  # slot 1, slot 2, then full

    limiter = RedisDomainRateLimiter(
        broker_url="redis://localhost:6379/0",
        prefix="orb",
        redis_client=mock_redis,
    )
    assert limiter.get_concurrency_key("github.com") == "orb:rate:concurrency:github.com"

    acq1 = await limiter.acquire("github.com", max_concurrent=2, timeout=1.0)
    acq2 = await limiter.acquire("github.com", max_concurrent=2, timeout=1.0)
    assert acq1 is True
    assert acq2 is True

    # Release slot
    await limiter.release("github.com")
    assert mock_redis.eval.call_count >= 3


@pytest.mark.asyncio
async def test_in_memory_page_cache():
    cache = InMemoryPageCache(prefix="orb")
    url = "https://huggingface.co/datasets/squad"
    assert cache.get_cache_key(url).startswith("orb:cache:page:")

    # Initial miss
    assert await cache.get_page(url) is None

    # Set and hit
    await cache.set_page(url, "# SQuAD Dataset Markdown Content", ttl_seconds=3600)
    cached = await cache.get_page(url)
    assert cached == "# SQuAD Dataset Markdown Content"

    # Bulk get_many
    many = await cache.get_many([url, "https://example.com/missing"])
    assert many[url] == "# SQuAD Dataset Markdown Content"
    assert many["https://example.com/missing"] is None


@pytest.mark.asyncio
async def test_redis_page_cache():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value="# Cached Redis Markdown")
    mock_redis.set = AsyncMock(return_value=True)

    cache = RedisPageCache(
        broker_url="redis://localhost:6379/0",
        prefix="orb",
        redis_client=mock_redis,
    )
    url = "https://news.ycombinator.com"
    key = cache.get_cache_key(url)
    assert key.startswith("orb:cache:page:")

    # Get page hit
    content = await cache.get_page(url)
    assert content == "# Cached Redis Markdown"
    mock_redis.get.assert_called_with(key)

    # Set page
    await cache.set_page(url, "# New Content", ttl_seconds=1800)
    mock_redis.set.assert_called_with(key, "# New Content", ex=1800)


@pytest.mark.asyncio
async def test_proxy_retrieval_with_cache_hit():
    mock_cache = MagicMock()
    mock_cache.get_page = AsyncMock(return_value="# Cached Page Content (No Network)")
    mock_cache.get_many = AsyncMock(return_value={"https://cached-site.com/item": "# Cached Page Content (No Network)"})

    retrieval = ProxyRetrieval(cache=mock_cache)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        result = await retrieval.retrieve_one("https://cached-site.com/item", use_cache=True)
        assert result == "# Cached Page Content (No Network)"
        # No outbound network call was made!
        assert not mock_post.called

    # Batch retrieve_many with cache hits
    batch_results = await retrieval.retrieve_many(["https://cached-site.com/item"], use_cache=True)
    assert batch_results["https://cached-site.com/item"] == "# Cached Page Content (No Network)"


def test_factories_swappable():
    cfg_mem = Settings(event_broker_backend="memory", cache_backend="memory", broker_key_prefix="orb")
    limiter_mem = RateLimiterFactory.get_limiter(cfg_mem)
    cache_mem = PageCacheFactory.get_cache(cfg_mem)
    assert isinstance(limiter_mem, InMemoryDomainRateLimiter)
    assert isinstance(cache_mem, InMemoryPageCache)

    cfg_redis = Settings(event_broker_backend="redis", broker_key_prefix="orb")
    limiter_redis = RateLimiterFactory.get_limiter(cfg_redis)
    cache_redis = PageCacheFactory.get_cache(cfg_redis)
    assert isinstance(limiter_redis, RedisDomainRateLimiter)
    assert isinstance(cache_redis, RedisPageCache)

    cfg_cache_redis = Settings(cache_backend="redis", broker_key_prefix="orb")
    limiter_cache_redis = RateLimiterFactory.get_limiter(cfg_cache_redis)
    assert isinstance(limiter_cache_redis, RedisDomainRateLimiter)

