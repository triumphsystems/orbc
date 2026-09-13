import logging
from collections.abc import Callable, Coroutine
from typing import Any

from core.events.broker import EventBroker, EventBrokerFactory, Subscriber
from core.events.types import OrbitEvent

logger = logging.getLogger("core.events")


class EventBus:
    """Unified event bus providing provider-agnostic event distribution across in-memory, Redis, and Cloud Pub/Sub."""

    _broker: EventBroker | None

    def __init__(self, broker: EventBroker | None = None):
        self._broker = broker

    @property
    def broker(self) -> EventBroker:
        if self._broker is None:
            self._broker = EventBrokerFactory.get_broker()
        return self._broker

    def subscribe(self, callback: Subscriber) -> None:
        self.broker.subscribe(callback)

    def unsubscribe(self, callback: Subscriber) -> None:
        self.broker.unsubscribe(callback)

    async def publish(self, event: OrbitEvent) -> None:
        await self.broker.publish(event)


# Global default event bus
event_bus = EventBus()

