"""Tests for the LLM client factory and provider resolution."""

import pytest
from unittest.mock import patch, MagicMock

from core.llm.factory import get_llm_client


@pytest.fixture(autouse=True)
def clear_factory_cache():
    """Clear the lru_cache before each test to ensure clean factory resolution."""
    get_llm_client.cache_clear()
    yield
    get_llm_client.cache_clear()


class TestLLMClientFactory:
    """Tests for provider-agnostic LLM client factory resolution."""

    @patch("core.llm.factory.get_settings")
    def test_factory_resolves_gemini(self, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_provider="gemini",
            llm_api_key="test-gemini-key",
            llm_model="gemini-2.5-flash",
        )
        with patch("core.llm.adapters.gemini.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            client = get_llm_client()
            from core.llm.adapters.gemini import GeminiLLMClient
            assert isinstance(client, GeminiLLMClient)

    @patch("core.llm.factory.get_settings")
    def test_factory_resolves_openrouter(self, mock_settings):
        mock_settings.return_value = MagicMock(llm_provider="openrouter")
        client = get_llm_client()
        from core.llm.adapters.openai_compat import OpenAICompatibleLLMClient
        assert isinstance(client, OpenAICompatibleLLMClient)

    @patch("core.llm.factory.get_settings")
    def test_factory_resolves_openai(self, mock_settings):
        mock_settings.return_value = MagicMock(llm_provider="openai")
        client = get_llm_client()
        from core.llm.adapters.openai_compat import OpenAICompatibleLLMClient
        assert isinstance(client, OpenAICompatibleLLMClient)

    @patch("core.llm.factory.get_settings")
    def test_factory_resolves_openai_compat(self, mock_settings):
        mock_settings.return_value = MagicMock(llm_provider="openai_compat")
        client = get_llm_client()
        from core.llm.adapters.openai_compat import OpenAICompatibleLLMClient
        assert isinstance(client, OpenAICompatibleLLMClient)

    @patch("core.llm.factory.get_settings")
    def test_factory_rejects_unknown_provider(self, mock_settings):
        mock_settings.return_value = MagicMock(llm_provider="unknown_provider")
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER 'unknown_provider'"):
            get_llm_client()

    @patch("core.llm.factory.get_settings")
    def test_factory_case_insensitive(self, mock_settings):
        mock_settings.return_value = MagicMock(llm_provider="OpenRouter")
        client = get_llm_client()
        from core.llm.adapters.openai_compat import OpenAICompatibleLLMClient
        assert isinstance(client, OpenAICompatibleLLMClient)

    @patch("core.llm.factory.get_settings")
    def test_factory_gemini_missing_api_key(self, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_provider="gemini",
            llm_api_key="",
        )
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            get_llm_client()

    @patch("core.llm.factory.get_settings")
    def test_factory_caches_result(self, mock_settings):
        """Factory should return the same cached instance on repeated calls."""
        mock_settings.return_value = MagicMock(llm_provider="openrouter")
        client_a = get_llm_client()
        client_b = get_llm_client()
        assert client_a is client_b
