"""Tests for the OpenAI-compatible LLM adapter (OpenRouter, OpenAI, Ollama, etc.)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx


class TestOpenAICompatibleLLMClient:
    """Tests for the OpenAI-compatible REST adapter."""

    @patch("core.llm.adapters.openai_compat.get_settings")
    @pytest.mark.asyncio
    async def test_call_json_success(self, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_api_key="sk-test",
            llm_model="anthropic/claude-3.5-sonnet",
            llm_base_url="https://openrouter.ai/api/v1",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"objective": "Track prices"}'}}]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from core.llm.adapters.openai_compat import OpenAICompatibleLLMClient
            client = OpenAICompatibleLLMClient()
            result = await client.call_json(
                system_prompt="You are a helpful assistant.",
                user_prompt="Track prices",
            )

            assert result == {"objective": "Track prices"}
            mock_client.post.assert_called_once()

    @patch("core.llm.adapters.openai_compat.get_settings")
    @pytest.mark.asyncio
    async def test_call_json_missing_api_key(self, mock_settings):
        mock_settings.return_value = MagicMock(llm_api_key="")

        from core.llm.adapters.openai_compat import OpenAICompatibleLLMClient
        client = OpenAICompatibleLLMClient()

        with pytest.raises(ValueError, match="LLM_API_KEY"):
            await client.call_json(system_prompt="test", user_prompt="test")

    @patch("core.llm.adapters.openai_compat.get_settings")
    @pytest.mark.asyncio
    async def test_call_json_api_error(self, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_api_key="sk-test",
            llm_model="gpt-4",
            llm_base_url="https://api.openai.com/v1",
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.json.return_value = {
            "error": {"message": "Rate limit exceeded"}
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from core.llm.adapters.openai_compat import OpenAICompatibleLLMClient
            client = OpenAICompatibleLLMClient()

            with pytest.raises(ValueError, match="LLM API Error \\(429\\)"):
                await client.call_json(system_prompt="test", user_prompt="test")

    @patch("core.llm.adapters.openai_compat.get_settings")
    @pytest.mark.asyncio
    async def test_call_json_no_choices(self, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_api_key="sk-test",
            llm_model="gpt-4",
            llm_base_url="https://api.openai.com/v1",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from core.llm.adapters.openai_compat import OpenAICompatibleLLMClient
            client = OpenAICompatibleLLMClient()

            with pytest.raises(ValueError, match="no choices"):
                await client.call_json(system_prompt="test", user_prompt="test")
