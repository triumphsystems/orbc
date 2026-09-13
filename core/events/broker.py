import asyncio
import inspect
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any

from core.config.settings import Settings, get_settings
from core.events.types import OrbitEvent

logger = logging.getLogger("core.events.broker")

Subscriber = Callable[[OrbitEvent], Coroutine[Any, Any, None] | Any]


class EventBroker(ABC):
    """Abstract interface for provider-agnostic event distribution and telemetry streaming."""

    prefix: str

    def __init__(self, prefix: str = "orb"):
        self.prefix = prefix.strip(":")

    def get_stream_key(self) -> str:
        """Returns global event stream key: e.g. orb:events:stream"""
        return f"{self.prefix}:events:stream"

    def get_run_channel(self, run_id: str) -> str:
        """Returns per-run telemetry channel: e.g. orb:events:run:{run_id}"""
        return f"{self.prefix}:events:run:{run_id}"

    @abstractmethod
    async def publish(self, event: OrbitEvent) -> None:
        """Publishes an event to the underlying messaging broker."""
        pass

    @abstractmethod
    def subscribe(self, callback: Subscriber) -> None:
        """Subscribes a listener callback to event notifications."""
        pass

    @abstractmethod
    def unsubscribe(self, callback: Subscriber) -> None:
        """Unsubscribes a listener callback."""
        pass


class InMemoryEventBroker(EventBroker):
    """In-memory event broker for local execution, tests, and standalone deployments."""

    def __init__(self, prefix: str = "orb"):
        super().__init__(prefix=prefix)
        self._subscribers: list[Subscriber] = []

    def subscribe(self, callback: Subscriber) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Subscriber) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def publish(self, event: OrbitEvent) -> None:
        logger.debug(f"[InMemoryBroker] Event: {event.event_type} (run={event.run_id})")
        for sub in list(self._subscribers):
            try:
                if inspect.iscoroutinefunction(sub):
                    await sub(event)
                else:
                    res = sub(event)
                    if inspect.isawaitable(res):
                        await res
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error in in-memory event subscriber for {event.event_type}: {e}")


class RedisEventBroker(EventBroker):
    """
    Redis-backed distributed event broker supporting Redis Streams and Pub/Sub.
    Keys formatted with configured prefix: orb:events:stream, orb:events:run:{id}.
    """

    def __init__(self, broker_url: str = "redis://localhost:6379/0", prefix: str = "orb", redis_client: Any = None):
        super().__init__(prefix=prefix)
        self.broker_url = broker_url
        self._client = redis_client
        self._local_fallback = InMemoryEventBroker(prefix=prefix)

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self.broker_url, decode_responses=True)
            except ImportError:
                logger.warning("redis package not installed. Falling back to in-memory event broker.")
                return None
            except Exception as err:
                logger.error(f"Failed to connect to Redis broker at {self.broker_url}: {err}")
                return None
        return self._client

    def subscribe(self, callback: Subscriber) -> None:
        self._local_fallback.subscribe(callback)

    def unsubscribe(self, callback: Subscriber) -> None:
        self._local_fallback.unsubscribe(callback)

    async def publish(self, event: OrbitEvent) -> None:
        # 1. Dispatch to local in-process subscribers
        await self._local_fallback.publish(event)

        # 2. Serialize event
        event_dict = {
            "event_type": event.event_type,
            "run_id": event.run_id,
            "automation_id": event.automation_id,
            "timestamp": event.timestamp.isoformat() if event.timestamp else "",
            "message": event.message or "",
            "payload": json.dumps(event.payload or {}),
        }

        # 3. Publish to Redis Stream and Run Channel
        client = await self._get_client()
        if client is not None:
            try:
                stream_key = self.get_stream_key()
                run_channel = self.get_run_channel(event.run_id)

                # Append to Redis Stream (auto-trimming to last ~10,000 events)
                if hasattr(client, "xadd"):
                    await client.xadd(stream_key, event_dict, maxlen=10000, approximate=True)

                # Publish to run-specific Pub/Sub channel for live UI streaming
                if hasattr(client, "publish"):
                    await client.publish(run_channel, json.dumps(event_dict))

            except Exception as err:
                logger.warning(f"Failed publishing event {event.event_type} to Redis: {err}")


class CloudPubSubEventBroker(EventBroker):
    """
    Cloud Pub/Sub event broker for serverless cloud environments.
    Topic name formatted with configured prefix: orb-events-topic.
    """

    def __init__(self, project_id: str, prefix: str = "orb", publisher_client: Any = None):
        super().__init__(prefix=prefix)
        self.project_id = project_id
        self._client = publisher_client
        self._local_fallback = InMemoryEventBroker(prefix=prefix)
        self.topic_name = f"{self.prefix}-events-topic"

    def subscribe(self, callback: Subscriber) -> None:
        self._local_fallback.subscribe(callback)

    def unsubscribe(self, callback: Subscriber) -> None:
        self._local_fallback.unsubscribe(callback)

    async def publish(self, event: OrbitEvent) -> None:
        # 1. Dispatch to local subscribers
        await self._local_fallback.publish(event)

        if not self.project_id:
            return

        event_payload = json.dumps({
            "event_type": event.event_type,
            "run_id": event.run_id,
            "automation_id": event.automation_id,
            "timestamp": event.timestamp.isoformat() if event.timestamp else "",
            "message": event.message or "",
            "payload": event.payload or {},
        }).encode("utf-8")

        try:
            if self._client is not None:
                topic_path = f"projects/{self.project_id}/topics/{self.topic_name}"
                if hasattr(self._client, "publish"):
                    res = self._client.publish(topic_path, event_payload)
                    if inspect.isawaitable(res):
                        await res
        except Exception as err:
            logger.warning(f"Cloud Pub/Sub publish failed for {event.event_type}: {err}")


class EventBrokerFactory:
    """Factory for creating and configuring swappable event brokers."""

    @classmethod
    def get_broker(cls, settings: Settings | None = None) -> EventBroker:
        cfg = settings or get_settings()
        backend = (cfg.event_broker_backend or "memory").strip().lower()
        prefix = cfg.broker_key_prefix or "orb"

        if backend == "redis":
            return RedisEventBroker(broker_url=cfg.broker_url, prefix=prefix)
        elif backend in {"pubsub", "cloud_pubsub"}:
            return CloudPubSubEventBroker(project_id=cfg.broker_project_id, prefix=prefix)

        return InMemoryEventBroker(prefix=prefix)
