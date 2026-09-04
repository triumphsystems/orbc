from unittest.mock import MagicMock, patch

import pytest

from core.llm.adapters.strands_model import get_strands_model


def test_get_strands_model_defaults_to_gemini():
    with patch("strands.models.gemini.GeminiModel", create=True) as mock_gemini:
        mock_instance = MagicMock()
        mock_gemini.return_value = mock_instance

        model = get_strands_model(provider="gemini", model_id="gemini-2.5-flash", api_key="test-key")
        assert model == mock_instance
        mock_gemini.assert_called_once_with(
            client_args={"api_key": "test-key"},
            model_config={"model_id": "gemini-2.5-flash"},
        )


def test_get_strands_model_bedrock_provider():
    with patch("strands.models.bedrock.BedrockModel", create=True) as mock_bedrock:
        mock_instance = MagicMock()
        mock_bedrock.return_value = mock_instance

        model = get_strands_model(provider="bedrock", model_id="anthropic.claude-3-5-sonnet")
        assert model == mock_instance
        mock_bedrock.assert_called_once_with(model_id="anthropic.claude-3-5-sonnet")


def test_get_strands_model_openai_provider():
    with patch("strands.models.openai.OpenAIModel", create=True) as mock_openai:
        mock_instance = MagicMock()
        mock_openai.return_value = mock_instance

        model = get_strands_model(provider="openai", model_id="gpt-4o", api_key="sk-test")
        assert model == mock_instance
        mock_openai.assert_called_once()
