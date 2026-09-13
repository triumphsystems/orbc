import json
from typing import Any, AsyncGenerator
from fastapi.responses import StreamingResponse

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "Content-Type": "text/event-stream",
    "X-Accel-Buffering": "no",
}


def format_sse(
    data: Any = None,
    event: str | None = None,
    event_id: str | None = None,
    retry_ms: int | None = 3000,
) -> str:
    """
    Formats a payload according to the W3C Server-Sent Events specification.
    Handles JSON serialization, multiline text formatting, event names, and reconnection retry hints.
    """
    lines = []
    if retry_ms is not None:
        lines.append(f"retry: {retry_ms}")
    if event_id is not None:
        lines.append(f"id: {event_id}")
    if event is not None:
        lines.append(f"event: {event}")

    if data is not None:
        if isinstance(data, (dict, list, bool, int, float)):
            serialized = json.dumps(data)
        elif hasattr(data, "model_dump_json"):
            serialized = data.model_dump_json()
        elif hasattr(data, "to_dict"):
            serialized = json.dumps(data.to_dict())
        else:
            serialized = str(data)

        for line in serialized.splitlines():
            lines.append(f"data: {line}")
    else:
        lines.append("data: {}")

    return "\n".join(lines) + "\n\n"


def format_sse_ping(comment: str = "ping") -> str:
    """Formats an SSE comment line used for keep-alive heartbeats."""
    return f": {comment}\n\n"


def sse_response(generator: AsyncGenerator[str, None], status_code: int = 200) -> StreamingResponse:
    """Wraps an asynchronous generator in a StreamingResponse with production SSE headers."""
    return StreamingResponse(
        generator,
        status_code=status_code,
        media_type="text/event-stream",
        headers=dict(SSE_HEADERS),
    )
