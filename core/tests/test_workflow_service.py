import pytest
from core.services.workflow_service import WorkflowService


def test_get_adapter_topology_modes():
    topology = WorkflowService.get_adapter_topology()
    assert len(topology) >= 7

    modes = {node["id"]: node.get("mode") for node in topology}
    # Check that 3 distinct modes exist
    assert "managed" in [node.get("mode") for node in topology]
    assert "both" in [node.get("mode") for node in topology]
    assert "custom" in [node.get("mode") for node in topology]

    # Verify Docling parser is managed
    doc_node = next(n for n in topology if n["label"] == "Document & Table Parser")
    assert doc_node["mode"] == "managed"

    # Verify Slack is custom
    slack_node = next(n for n in topology if n["label"] == "Slack Notifications")
    assert slack_node["mode"] == "custom"


def test_resolve_secret_and_masked_placeholders():
    # 1. Unmasked submitted value is respected
    val = WorkflowService._resolve_secret("custom_1", "real-api-key-123", "api_key", "daemon-fallback")
    assert val == "real-api-key-123"

    # 2. Masked submitted value falls back to saved custom config
    WorkflowService._custom_adapter_configs["custom_1"] = {"api_key": "saved-vault-key-456"}
    val_saved = WorkflowService._resolve_secret("custom_1", "••••••••1234", "api_key", "daemon-fallback")
    assert val_saved == "saved-vault-key-456"

    # 3. Unicode bullet placeholder also falls back to saved config
    val_unicode = WorkflowService._resolve_secret("custom_1", "\u2022\u2022\u2022\u2022", "api_key", "daemon-fallback")
    assert val_saved == "saved-vault-key-456"

    # 4. Both submitted and saved are masked -> falls back to daemon setting
    WorkflowService._custom_adapter_configs["custom_2"] = {"api_key": "••••••••"}
    val_fallback = WorkflowService._resolve_secret("custom_2", "••••••••", "api_key", "daemon-fallback")
    assert val_fallback == "daemon-fallback"

    # 5. Empty submitted value with tuple of fallback keys
    WorkflowService._custom_adapter_configs["custom_db"] = {"database_url": "postgresql://usr:pwd@localhost/db"}
    val_multi = WorkflowService._resolve_secret("custom_db", "", ("connection_uri", "database_url"), "sqlite://")
    assert val_multi == "postgresql://usr:pwd@localhost/db"



@pytest.mark.asyncio
async def test_test_adapter_connection():
    # Test S3 connection probe with mock
    from unittest.mock import AsyncMock, MagicMock, patch
    mock_head_resp = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head:
        mock_head.return_value = mock_head_resp
        ok, msg = await WorkflowService.test_adapter_connection(
            "7", {"bucket_name": "orbit-test", "access_key": "AKIA123", "secret_key": "secret123"}
        )
        assert ok is True
        assert "orbit-test" in msg

    # Test Database connection probe with sqlite in-memory
    ok_db, msg_db = await WorkflowService.test_adapter_connection(
        "sql_database", {"connection_uri": "sqlite:///:memory:"}
    )
    assert ok_db is True
    assert "verified" in msg_db

    # Test Email connection probe with invalid recipient
    ok_email_inv, msg_email_inv = await WorkflowService.test_adapter_connection(
        "email_alert", {"recipient_email": "invalid-address"}
    )
    assert ok_email_inv is False
    assert "valid recipient email" in msg_email_inv

    # Test Email custom mode without host
    ok_smtp_fail, msg_smtp_fail = await WorkflowService.test_adapter_connection(
        "10", {"mode": "custom", "recipient_email": "admin@company.com", "smtp_host": ""}
    )
    assert ok_smtp_fail is False
    assert "SMTP Host is required" in msg_smtp_fail

    # Test Slack probe without URL
    ok_slack_no_url, msg_slack_no_url = await WorkflowService.test_adapter_connection(
        "slack_alert", {"webhook_url": ""}
    )
    assert ok_slack_no_url is False
    assert "not configured" in msg_slack_no_url

    # Test Slack probe with mock
    from unittest.mock import AsyncMock, MagicMock, patch
    mock_resp = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        ok_slack, msg_slack = await WorkflowService.test_adapter_connection(
            "slack_alert", {"webhook_url": "https://hooks.slack.com/services/T00/B00/X123"}
        )
        assert ok_slack is True
        assert "verified" in msg_slack

    # Test Webhook probe with mock
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        ok_wh, msg_wh = await WorkflowService.test_adapter_connection(
            "webhook_alert", {"webhook_url": "https://api.external.com/events"}
        )
        assert ok_wh is True
        assert "reached and acknowledged" in msg_wh
