"""OpenAI-compatible REST adapter (OpenRouter, OpenAI, Ollama, etc.)."""

from typing import Any

import httpx

from core.config.settings import get_settings
from core.llm.utils import parse_llm_json


class OpenAICompatibleLLMClient:
    """OpenAI-compatible LLM client supporting JSON outputs via REST /chat/completions."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send prompt to an OpenAI-compatible endpoint and receive structured JSON response."""
        if not self.settings.llm_api_key:
            raise ValueError("LLM_API_KEY is not configured for OpenAI-compatible provider.")

        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                error_msg = resp.text
                try:
                    err_json = resp.json()
                    if "error" in err_json and "message" in err_json["error"]:
                        error_msg = err_json["error"]["message"]
                except Exception:  # noqa: BLE001
                    pass
                raise ValueError(f"LLM API Error ({resp.status_code}): {error_msg}")

            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"LLM API returned no choices in response: {data}")

        content = choices[0]["message"]["content"]
        return parse_llm_json(content)
