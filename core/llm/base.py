from typing import Any, Protocol


class LLMClient(Protocol):
    """Protocol for LLM communication."""

    async def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send prompt to LLM and receive structured JSON response."""
        ...
