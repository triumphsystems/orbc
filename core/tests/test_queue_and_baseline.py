import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agent.baseline_cache import (
    BaselineCacheFactory,
    InMemoryBaselineCache,
    RedisBaselineCache,
)
from core.agent.condition import ConditionEvaluator
from core.config.settings import Settings
from core.scheduler.task_queue import (
    InMemoryTaskQueue,
    RedisTaskQueue,
    TaskQueueFactory,
)


@pytest.mark.asyncio
async def test_in_memory_task_queue():
    queue = InMemoryTaskQueue(prefix="orb")
    assert queue.get_pending_queue_key() == "orb:queue:missions:pending"
    assert queue.get_active_queue_key() == "orb:queue:missions:active"

    # Enqueue
    task_id = await queue.enqueue({"automation_id": "auto-101", "goal": "Find GPUs"})
    assert task_id is not None
    assert await queue.get_pending_count() == 1

    # Dequeue
    task = await queue.dequeue(timeout_seconds=1)
    assert task is not None
    assert task["automation_id"] == "auto-101"
    assert task["task_id"] == task_id
    assert await queue.get_pending_count() == 0

    # Ack
    await queue.ack(task_id)


@pytest.mark.asyncio
async def test_redis_task_queue():
    mock_redis = MagicMock()
    mock_redis.lpush = AsyncMock(return_value=1)
    mock_redis.brpop = AsyncMock(return_value=("orb:queue:missions:pending", '{"task_id": "t-1", "automation_id": "auto-99"}'))
    mock_redis.llen = AsyncMock(return_value=1)

    queue = RedisTaskQueue(
        broker_url="redis://localhost:6379/0",
        prefix="orb",
        redis_client=mock_redis,
    )
    assert queue.get_pending_queue_key() == "orb:queue:missions:pending"

    # Enqueue
    tid = await queue.enqueue({"automation_id": "auto-99"})
    assert tid is not None
    assert mock_redis.lpush.called

    # Dequeue
    task = await queue.dequeue(timeout_seconds=2)
    assert task["automation_id"] == "auto-99"
    assert task["task_id"] == "t-1"


@pytest.mark.asyncio
async def test_in_memory_baseline_cache():
    cache = InMemoryBaselineCache(prefix="orb")
    assert cache.get_baseline_key("auto-123") == "orb:baseline:auto-123"

    # Initial miss
    assert await cache.get_baseline("auto-123") is None

    # Set and hit
    await cache.set_baseline("auto-123", {"price_min": 250.0, "price_avg": 300.0})
    base = await cache.get_baseline("auto-123")
    assert base == {"price_min": 250.0, "price_avg": 300.0}

    # Update from records
    records = [
        {"data": {"salary": 150000}},
        {"data": {"salary": 180000}},
    ]
    computed = await cache.update_from_records("auto-jobs", records)
    assert computed["salary_min"] == 150000
    assert computed["salary_max"] == 180000
    assert computed["salary_avg"] == 165000


@pytest.mark.asyncio
async def test_redis_baseline_cache():
    mock_redis = MagicMock()
    mock_redis.hgetall = AsyncMock(return_value={"price_min": "100.0", "price_max": "200.0"})
    mock_redis.hset = AsyncMock(return_value=2)
    mock_redis.expire = AsyncMock(return_value=True)

    cache = RedisBaselineCache(
        broker_url="redis://localhost:6379/0",
        prefix="orb",
        redis_client=mock_redis,
    )
    assert cache.get_baseline_key("auto-777") == "orb:baseline:auto-777"

    # Get
    res = await cache.get_baseline("auto-777")
    assert res == {"price_min": 100.0, "price_max": 200.0}

    # Set
    await cache.set_baseline("auto-777", {"price_min": 120.0})
    assert mock_redis.hset.called
    assert mock_redis.expire.called


def test_condition_evaluation_with_baseline_metrics():
    evaluator = ConditionEvaluator()
    curr_records = [
        {"url": "https://example.com/item1", "data": {"price": 180.0}},
        {"url": "https://example.com/item2", "data": {"price": 190.0}},
    ]

    # Baseline: min price was 220.0; now dropped to 180.0 (18.18% drop)
    baseline_metrics = {"price_min": 220.0, "price_max": 250.0}

    matched, msg = evaluator.evaluate(
        "price drops by 15%",
        curr_records,
        baseline_metrics=baseline_metrics,
    )
    assert matched is True
    assert "18.2%" in msg


def test_factories_swappable():
    cfg_mem = Settings(event_broker_backend="memory", broker_key_prefix="orb")
    queue_mem = TaskQueueFactory.get_queue(cfg_mem)
    cache_mem = BaselineCacheFactory.get_cache(cfg_mem)
    assert isinstance(queue_mem, InMemoryTaskQueue)
    assert isinstance(cache_mem, InMemoryBaselineCache)

    cfg_redis = Settings(event_broker_backend="redis", broker_key_prefix="orb")
    queue_redis = TaskQueueFactory.get_queue(cfg_redis)
    cache_redis = BaselineCacheFactory.get_cache(cfg_redis)
    assert isinstance(queue_redis, RedisTaskQueue)
    assert isinstance(cache_redis, RedisBaselineCache)
