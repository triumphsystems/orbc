"""Provider-agnostic LLM client factory.

Resolves the correct adapter based on the ``LLM_PROVIDER`` setting so that
consumers never import provider-specific code directly.
"""

from functools import lru_cache

from core.config.settings import get_settings
from core.llm.base import LLMClient


@lru_cache
def get_llm_client() -> LLMClient:
    """Factory that resolves the correct LLM adapter based on LLM_PROVIDER setting."""
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "gemini":
        from core.llm.adapters.gemini import GeminiLLMClient

        return GeminiLLMClient()
    elif provider in ("openrouter", "openai", "openai_compat"):
        from core.llm.adapters.openai_compat import OpenAICompatibleLLMClient

        return OpenAICompatibleLLMClient()
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. "
            f"Supported: 'gemini', 'openrouter', 'openai', 'openai_compat'"
        )
