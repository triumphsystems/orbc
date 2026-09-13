import pytest
from unittest.mock import patch, MagicMock
from orbit.config import get_mcp_settings


def test_mcp_settings_transport_defaults():
    get_mcp_settings.cache_clear()
    settings = get_mcp_settings()
    assert settings.mcp_transport in ("stdio", "sse")
    assert settings.mcp_port == 8001
    assert settings.mcp_host == "0.0.0.0"


def test_mcp_server_module_exports_app():
    from orbit.server import app, main
    assert callable(main)
