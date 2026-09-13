from fastapi.testclient import TestClient
from core.app import app

client = TestClient(app)


def test_get_workflow_topology():
    response = client.get("/api/v1/workflows/topology")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 7

    # Verify modes are serialized properly
    modes = [node.get("mode") for node in data]
    assert "managed" in modes
    assert "both" in modes
    assert "custom" in modes


def test_deploy_workflow():
    payload = {
        "nodes": [
            {"id": "1", "label": "Schedule Trigger", "config": {}},
            {"id": "2", "label": "S3 Object Storage", "config": {"bucket_name": "my-bucket"}},
        ]
    }
    response = client.post("/api/v1/workflows/deploy", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "deployed"
    assert "2 active adapter stages" in res["message"]


def test_test_adapter_connection_api():
    from unittest.mock import AsyncMock, MagicMock, patch
    mock_s3 = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head:
        mock_head.return_value = mock_s3
        payload = {
            "adapter_id": "7",
            "config": {"bucket_name": "orbit-production", "access_key": "AKIA123", "secret_key": "secret123"}
        }
        response = client.post("/api/v1/workflows/test-connection", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "orbit-production" in data["message"]

    # Test Database probe via API
    db_payload = {
        "adapter_id": "sql_database",
        "config": {"connection_uri": "sqlite:///:memory:"}
    }
    db_resp = client.post("/api/v1/workflows/test-connection", json=db_payload)
    assert db_resp.status_code == 200
    db_data = db_resp.json()
    assert db_data["success"] is True
    assert "verified" in db_data["message"]

    # Test Email probe via API with invalid recipient
    email_payload = {
        "adapter_id": "email_alert",
        "config": {"recipient_email": "bad_email_format"}
    }
    email_resp = client.post("/api/v1/workflows/test-connection", json=email_payload)
    assert email_resp.status_code == 200
    email_data = email_resp.json()
    assert email_data["success"] is False

    # Test Email probe via API with valid recipient and mock
    from unittest.mock import AsyncMock, patch
    with patch("core.adapters.communication.email.EmailNotificationAdapter.test_managed_connection", new_callable=AsyncMock) as mock_test:
        mock_test.return_value = (True, "Live managed email probe verified to user@example.com")
        valid_payload = {
            "adapter_id": "email_alert",
            "config": {"recipient_email": "user@example.com", "api_key": "test-key"}
        }
        res_valid = client.post("/api/v1/workflows/test-connection", json=valid_payload)
        assert res_valid.status_code == 200
        assert res_valid.json()["success"] is True
        assert "user@example.com" in res_valid.json()["message"]

    # Test Slack probe via API with mock
    from unittest.mock import MagicMock
    mock_resp = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        slack_payload = {
            "adapter_id": "slack_alert",
            "config": {"webhook_url": "https://hooks.slack.com/services/T1/B1/X1"}
        }
        res_slack = client.post("/api/v1/workflows/test-connection", json=slack_payload)
        assert res_slack.status_code == 200
        assert res_slack.json()["success"] is True
        assert "verified" in res_slack.json()["message"]

    # Test Outbound Webhook probe via API with mock
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        wh_payload = {
            "adapter_id": "webhook_alert",
            "config": {"webhook_url": "https://api.domain.com/webhook", "signing_secret": "whsec_123"}
        }
        res_wh = client.post("/api/v1/workflows/test-connection", json=wh_payload)
        assert res_wh.status_code == 200
        assert res_wh.json()["success"] is True
