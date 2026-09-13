"""Tests for the Gemini LLM adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGeminiLLMClient:
    """Tests for the Google Gemini adapter (google-genai SDK)."""

    @patch("core.llm.adapters.gemini.get_settings")
    @patch("core.llm.adapters.gemini.genai")
    @pytest.mark.asyncio
    async def test_call_json_success(self, mock_genai, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_api_key="test-key",
            llm_model="gemini-2.5-flash",
        )
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"objective": "Track prices", "domain": "e-commerce"}'
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        from core.llm.adapters.gemini import GeminiLLMClient
        client = GeminiLLMClient()
        result = await client.call_json(
            system_prompt="You are a helpful assistant.",
            user_prompt="Track GPU prices",
            temperature=0.0,
        )

        assert result == {"objective": "Track prices", "domain": "e-commerce"}
        mock_client.aio.models.generate_content.assert_called_once()

    @patch("core.llm.adapters.gemini.get_settings")
    @patch("core.llm.adapters.gemini.genai")
    @pytest.mark.asyncio
    async def test_call_json_empty_response(self, mock_genai, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_api_key="test-key",
            llm_model="gemini-2.5-flash",
        )
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = ""
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        from core.llm.adapters.gemini import GeminiLLMClient
        client = GeminiLLMClient()

        with pytest.raises(ValueError, match="empty response"):
            await client.call_json(
                system_prompt="test",
                user_prompt="test",
            )

    @patch("core.llm.adapters.gemini.get_settings")
    def test_missing_api_key_raises(self, mock_settings):
        mock_settings.return_value = MagicMock(llm_api_key="")

        from core.llm.adapters.gemini import GeminiLLMClient
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            GeminiLLMClient()

    @patch("core.llm.adapters.gemini.get_settings")
    @patch("core.llm.adapters.gemini.genai")
    @pytest.mark.asyncio
    async def test_call_json_handles_fenced_json(self, mock_genai, mock_settings):
        """Gemini sometimes returns JSON wrapped in markdown code fences."""
        mock_settings.return_value = MagicMock(
            llm_api_key="test-key",
            llm_model="gemini-2.5-flash",
        )
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '```json\n{"key": "value"}\n```'
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        from core.llm.adapters.gemini import GeminiLLMClient
        client = GeminiLLMClient()
        result = await client.call_json(system_prompt="test", user_prompt="test")
        assert result == {"key": "value"}
