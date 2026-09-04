import logging
from typing import Any

from core.config.settings import get_settings

logger = logging.getLogger("core.llm.adapters.strands_model")


def get_strands_model(
    provider: str | None = None,
    model_id: str | None = None,
    api_key: str | None = None,
) -> Any:
    """
    Returns a configured Strands Agents Model instance respecting Orbit's provider-agnostic settings.
    Defaults to Google Gemini (gemini-2.5-flash) using Orbit's single canonical LLM_API_KEY.
    Supports Amazon Bedrock, Anthropic, OpenAI, and Ollama.
    """
    settings = get_settings()
    eff_provider = (provider or settings.llm_provider or "gemini").lower()
    eff_model = model_id or settings.llm_model or "gemini-2.5-flash"
    eff_key = api_key or settings.llm_api_key

    if eff_provider in ("gemini", "google"):
        try:
            from strands.models.gemini import GeminiModel

            return GeminiModel(
                client_args={"api_key": eff_key} if eff_key else {},
                model_config={"model_id": eff_model},
            )
        except Exception as e:
            logger.warning("Failed initializing native Strands GeminiModel: %s", e)

    elif eff_provider in ("bedrock", "aws"):
        try:
            from strands.models.bedrock import BedrockModel

            return BedrockModel(model_id=eff_model)
        except Exception as e:
            logger.warning("Failed initializing Strands BedrockModel: %s", e)

    elif eff_provider in ("anthropic", "claude"):
        try:
            from strands.models.anthropic import AnthropicModel

            return AnthropicModel(
                client_args={"api_key": eff_key} if eff_key else {},
                model_config={"model_id": eff_model},
            )
        except Exception as e:
            logger.warning("Failed initializing Strands AnthropicModel: %s", e)

    elif eff_provider in ("openai", "openrouter"):
        try:
            from strands.models.openai import OpenAIModel

            client_args: dict[str, Any] = {}
            if eff_key:
                client_args["api_key"] = eff_key
            if settings.llm_base_url:
                client_args["base_url"] = settings.llm_base_url
            return OpenAIModel(
                client_args=client_args,
                model_config={"model_id": eff_model},
            )
        except Exception as e:
            logger.warning("Failed initializing Strands OpenAIModel: %s", e)

    elif eff_provider in ("ollama", "local"):
        try:
            from strands.models.ollama import OllamaModel

            return OllamaModel(model_id=eff_model)
        except Exception as e:
            logger.warning("Failed initializing Strands OllamaModel: %s", e)

    # Fallback to GeminiModel default
    try:
        from strands.models.gemini import GeminiModel

        return GeminiModel(
            client_args={"api_key": eff_key} if eff_key else {},
            model_config={"model_id": eff_model},
        )
    except Exception as e:
        logger.error("All Strands model initializations failed: %s", e)
        raise
