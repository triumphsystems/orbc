from typing import Any, Protocol


class Notifier(Protocol):
    """Protocol for dispatching notifications and alerts."""

    async def notify(
        self, title: str, message: str, payload: dict[str, Any] | None = None
    ) -> bool:
        ...
