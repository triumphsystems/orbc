from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OrbitEvent:
    event_type: str
    run_id: str
    automation_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = field(default_factory=dict)
    message: str | None = None
