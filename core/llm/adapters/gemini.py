"""Google Gemini adapter implementing the LLMClient protocol via google-genai SDK."""

from typing import Any

from google import genai
from google.genai import types

from core.config.settings import get_settings
from core.llm.utils import parse_llm_json


class GeminiLLMClient:
    """Google Gemini adapter using the google-genai SDK for structured JSON completions."""

    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.llm_api_key:
            raise ValueError("LLM_API_KEY (Gemini API key) is not configured.")
        self._client = genai.Client(api_key=self.settings.llm_api_key)

    async def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send prompt to Gemini and receive structured JSON response."""
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            response_mime_type="application/json",
        )

        response = await self._client.aio.models.generate_content(
            model=self.settings.llm_model,
            contents=user_prompt,
            config=config,
        )

        if not response.text:
            raise ValueError(f"Gemini API returned empty response: {response}")

        return parse_llm_json(response.text)
