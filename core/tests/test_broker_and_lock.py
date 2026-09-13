import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config.settings import Settings
from core.events.broker import (
    CloudPubSubEventBroker,
    EventBrokerFactory,
    InMemoryEventBroker,
    RedisEventBroker,
)
from core.events.bus import EventBus
from core.events.types import OrbitEvent
from core.scheduler.lock import DistributedLock, InMemoryLock, LockFactory, RedisLock


@pytest.mark.asyncio
async def test_in_memory_event_broker():
    broker = InMemoryEventBroker(prefix="orb")
    assert broker.get_stream_key() == "orb:events:stream"
    assert broker.get_run_channel("run-123") == "orb:events:run:run-123"

    received_events = []

    def sync_listener(evt: OrbitEvent):
        received_events.append(evt)

    async def async_listener(evt: OrbitEvent):
        received_events.append(evt)

    broker.subscribe(sync_listener)
    broker.subscribe(async_listener)

    event = OrbitEvent(
        event_type="run.started",
        run_id="run-123",
        automation_id="auto-456",
        message="Starting autonomous mission",
    )
    await broker.publish(event)

    assert len(received_events) == 2
    assert received_events[0].event_type == "run.started"
    assert received_events[1].run_id == "run-123"


@pytest.mark.asyncio
async def test_redis_event_broker_keys_and_publishing():
    mock_redis = MagicMock()
    mock_redis.xadd = AsyncMock(return_value="1700000000000-0")
    mock_redis.publish = AsyncMock(return_value=1)

    broker = RedisEventBroker(
        broker_url="redis://localhost:6379/0",
        prefix="orb",
        redis_client=mock_redis,
    )

    assert broker.get_stream_key() == "orb:events:stream"
    assert broker.get_run_channel("run-999") == "orb:events:run:run-999"

    event = OrbitEvent(
        event_type="stage.completed",
        run_id="run-999",
        automation_id="auto-111",
        message="Discovery completed",
    )
    await broker.publish(event)

    # Verify Redis Stream XADD call with orb:events:stream
    assert mock_redis.xadd.called
    stream_key, payload = mock_redis.xadd.call_args[0][:2]
    assert stream_key == "orb:events:stream"
    assert payload["event_type"] == "stage.completed"
    assert payload["run_id"] == "run-999"

    # Verify Redis Pub/Sub call with orb:events:run:run-999
    assert mock_redis.publish.called
    pub_channel, pub_data = mock_redis.publish.call_args[0][:2]
    assert pub_channel == "orb:events:run:run-999"
    assert "stage.completed" in pub_data


@pytest.mark.asyncio
async def test_cloud_pubsub_event_broker():
    mock_pubsub = MagicMock()
    mock_pubsub.publish = MagicMock(return_value=None)

    broker = CloudPubSubEventBroker(
        project_id="orbit-gcp-prod",
        prefix="orb",
        publisher_client=mock_pubsub,
    )

    assert broker.topic_name == "orb-events-topic"

    received = []
    def listener(evt: OrbitEvent):
        received.append(evt)

    broker.subscribe(listener)

    event = OrbitEvent(
        event_type="run.completed",
        run_id="run-555",
        automation_id="auto-555",
    )
    await broker.publish(event)

    assert len(received) == 1
    assert mock_pubsub.publish.called
    topic_path = mock_pubsub.publish.call_args[0][0]
    assert topic_path == "projects/orbit-gcp-prod/topics/orb-events-topic"

    broker.unsubscribe(listener)
    await broker.publish(event)
    assert len(received) == 1


def test_event_broker_factory_swappable():
    # Memory
    cfg_mem = Settings(event_broker_backend="memory", broker_key_prefix="orb")
    b_mem = EventBrokerFactory.get_broker(cfg_mem)
    assert isinstance(b_mem, InMemoryEventBroker)
    assert b_mem.prefix == "orb"

    # Redis
    cfg_redis = Settings(event_broker_backend="redis", broker_url="redis://test:6379/0", broker_key_prefix="orb")
    b_redis = EventBrokerFactory.get_broker(cfg_redis)
    assert isinstance(b_redis, RedisEventBroker)
    assert b_redis.get_stream_key() == "orb:events:stream"

    # Cloud PubSub
    cfg_ps = Settings(event_broker_backend="pubsub", broker_project_id="my-gcp-proj", broker_key_prefix="orb")
    b_ps = EventBrokerFactory.get_broker(cfg_ps)
    assert isinstance(b_ps, CloudPubSubEventBroker)
    assert b_ps.topic_name == "orb-events-topic"


@pytest.mark.asyncio
async def test_in_memory_distributed_lock():
    lock = InMemoryLock(prefix="orb")
    assert lock.get_lock_key("scheduler:tick") == "orb:lock:scheduler:tick"

    # 1. Acquire lock
    acq1 = await lock.acquire("scheduler:tick", timeout_seconds=10)
    assert acq1 is True

    # 2. Re-acquire conflict rejection
    acq2 = await lock.acquire("scheduler:tick", timeout_seconds=10)
    assert acq2 is False

    # 3. Release lock
    await lock.release("scheduler:tick")

    # 4. Acquire again after release
    acq3 = await lock.acquire("scheduler:tick", timeout_seconds=10)
    assert acq3 is True


@pytest.mark.asyncio
async def test_redis_distributed_lock():
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.eval = AsyncMock(return_value=1)

    lock = RedisLock(
        broker_url="redis://localhost:6379/0",
        prefix="orb",
        redis_client=mock_redis,
    )
    assert lock.get_lock_key("scheduler:tick") == "orb:lock:scheduler:tick"

    # Acquire
    acquired = await lock.acquire("scheduler:tick", timeout_seconds=25)
    assert acquired is True
    assert mock_redis.set.called
    set_call_args = mock_redis.set.call_args
    assert set_call_args[0][0] == "orb:lock:scheduler:tick"
    assert set_call_args[1]["nx"] is True
    assert set_call_args[1]["ex"] == 25

    # Release
    await lock.release("scheduler:tick")
    assert mock_redis.eval.called


@pytest.mark.asyncio
async def test_lock_factory():
    cfg_mem = Settings(event_broker_backend="memory", broker_key_prefix="orb")
    lock_mem = LockFactory.get_lock(cfg_mem)
    assert isinstance(lock_mem, InMemoryLock)

    cfg_redis = Settings(event_broker_backend="redis", broker_key_prefix="orb")
    lock_redis = LockFactory.get_lock(cfg_redis)
    assert isinstance(lock_redis, RedisLock)
