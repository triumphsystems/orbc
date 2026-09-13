import asyncio
import pytest
from core.cache.base import BaseCache
from core.cache.memory import InMemoryCache
from core.cache.redis import RedisCache
from core.cache.service import CacheService, cache_service


@pytest.mark.asyncio
async def test_in_memory_cache_basic_ops():
    cache = InMemoryCache(prefix="test")
    key = cache.build_key("sample", "key1")

    # 1. Set & Get
    await cache.set(key, {"foo": "bar"}, ttl_seconds=10)
    res = await cache.get(key)
    assert res == {"foo": "bar"}

    # 2. Key exists check
    assert await cache.get(key) is not None

    # 3. Delete
    deleted = await cache.delete(key)
    assert deleted is True
    assert await cache.get(key) is None


@pytest.mark.asyncio
async def test_in_memory_cache_ttl_expiry():
    cache = InMemoryCache(prefix="test")
    key = cache.build_key("temp", "expiring_key")

    # Set with 0.1s TTL
    await cache.set(key, "hello", ttl_seconds=0.05)
    assert await cache.get(key) == "hello"

    await asyncio.sleep(0.08)
    assert await cache.get(key) is None


@pytest.mark.asyncio
async def test_in_memory_cache_delete_pattern():
    cache = InMemoryCache(prefix="test")
    k1 = cache.build_key("warehouse:auto1", "page1")
    k2 = cache.build_key("warehouse:auto1", "page2")
    k3 = cache.build_key("warehouse:auto2", "page1")

    await cache.set(k1, "data1")
    await cache.set(k2, "data2")
    await cache.set(k3, "data3")

    # Invalidate auto1
    count = await cache.delete_pattern("test:warehouse:auto1:*")
    assert count == 2
    assert await cache.get(k1) is None
    assert await cache.get(k2) is None
    assert await cache.get(k3) == "data3"


@pytest.mark.asyncio
async def test_cache_service_get_or_set():
    service = CacheService(backend=InMemoryCache(prefix="test_srv"))
    key = service.key_for_dossier("run-12345")

    call_count = 0

    async def factory():
        nonlocal call_count
        call_count += 1
        return "generated_dossier_data"

    # First call runs factory
    val1 = await service.get_or_set(key, factory, ttl_seconds=60)
    assert val1 == "generated_dossier_data"
    assert call_count == 1

    # Second call hits cache
    val2 = await service.get_or_set(key, factory, ttl_seconds=60)
    assert val2 == "generated_dossier_data"
    assert call_count == 1


@pytest.mark.asyncio
async def test_cache_service_probe_invalidation():
    service = CacheService(backend=InMemoryCache(prefix="test_probe"))
    k_probe1 = service.key_for_probe("7", {"bucket_name": "orbit-test"})
    k_probe2 = service.key_for_probe("8", {"connection_uri": "sqlite://"})

    await service.set(k_probe1, [True, "OK"], ttl_seconds=30)
    await service.set(k_probe2, [True, "DB OK"], ttl_seconds=30)

    assert await service.get(k_probe1) == [True, "OK"]
    assert await service.get(k_probe2) == [True, "DB OK"]

    # Invalidate all probes
    deleted = await service.invalidate_all_probes()
    assert deleted == 2
    assert await service.get(k_probe1) is None
    assert await service.get(k_probe2) is None


@pytest.mark.asyncio
async def test_redis_cache_fallback():
    # Test RedisCache fallback when Redis is unconfigured/unreachable
    redis_cache = RedisCache(broker_url="redis://localhost:59999/9", prefix="test_fallback")
    key = redis_cache.build_key("test", "item")

    await redis_cache.set(key, {"status": "active"}, ttl_seconds=60)
    result = await redis_cache.get(key)
    assert result == {"status": "active"}

    deleted = await redis_cache.delete(key)
    assert deleted is True
    assert await redis_cache.get(key) is None
