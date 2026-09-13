from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from core.adapters.communication.email import EmailNotificationAdapter
from core.notifications.service import NotificationService


@pytest.mark.asyncio
async def test_email_adapter_send_email_success():
    adapter = EmailNotificationAdapter(
        api_key="test_email_api_key_123",
        sender_address="Orbit Alerts <alerts@orbit.dev>",
        base_url="https://api.email-gateway.internal/v1/emails",
    )

    mock_resp = MagicMock(status_code=200, text='{"id": "msg_123"}')
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        success = await adapter.send_email(
            to="user@example.com",
            subject="Test Subject",
            html_body="<p>Hello world</p>",
            text_body="Hello world",
        )

        assert success is True
        assert mock_post.called

        called_url = mock_post.call_args.args[0]
        assert called_url == "https://api.email-gateway.internal/v1/emails"

        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test_email_api_key_123"
        assert headers["Content-Type"] == "application/json"

        json_body = mock_post.call_args.kwargs["json"]
        assert json_body["from"] == "Orbit Alerts <alerts@orbit.dev>"
        assert json_body["to"] == ["user@example.com"]
        assert json_body["subject"] == "Test Subject"
        assert json_body["html"] == "<p>Hello world</p>"
        assert json_body["text"] == "Hello world"


@pytest.mark.asyncio
async def test_email_adapter_send_alert_formatting():
    adapter = EmailNotificationAdapter(
        api_key="test_key",
        sender_address="Orbit Alerts <alerts@orbit.dev>",
    )

    mock_resp = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        success = await adapter.send_alert(
            title="Price Drop Alert",
            message="GPU price dropped below $300",
            recipient_email="analyst@domain.com",
            payload={"price": 289, "merchant": "TechStore"},
            dossier_url="https://s3.amazonaws.com/orbit-exports/report.pdf",
        )

        assert success is True
        json_body = mock_post.call_args.kwargs["json"]
        assert json_body["to"] == ["analyst@domain.com"]
        assert "GPU price dropped below $300" in json_body["html"]
        assert "Download Intelligence Dossier" in json_body["html"]
        assert "https://s3.amazonaws.com/orbit-exports/report.pdf" in json_body["html"]


@pytest.mark.asyncio
async def test_email_adapter_missing_api_key_safe_skip():
    adapter = EmailNotificationAdapter(api_key="", sender_address="alerts@orbit.dev")
    success = await adapter.send_email(to="user@example.com", subject="Test", html_body="<p>Test</p>")
    assert success is False


@pytest.mark.asyncio
async def test_notification_service_routes_to_email():
    service = NotificationService()
    service.email_adapter = MagicMock()
    service.email_adapter.send_alert = AsyncMock(return_value=True)

    success = await service.notify(
        title="Flight Alert",
        message="Flight found for $200",
        recipient_email="traveler@example.com",
        channel="email",
        dossier_url="https://orbit.dev/dossier/1",
    )

    assert success is True
    assert service.email_adapter.send_alert.called
    args = service.email_adapter.send_alert.call_args.kwargs
    assert args["recipient_email"] == "traveler@example.com"
    assert args["title"] == "Flight Alert"
    assert args["dossier_url"] == "https://orbit.dev/dossier/1"


@pytest.mark.asyncio
async def test_email_adapter_test_managed_connection():
    # Without api key
    ok_no_key, msg_no_key = await EmailNotificationAdapter.test_managed_connection(
        recipient_email="test@domain.com", api_key=""
    )
    assert ok_no_key is False
    assert "missing EMAIL_API_KEY" in msg_no_key

    # Without recipient email
    ok_no_rec, msg_no_rec = await EmailNotificationAdapter.test_managed_connection(
        recipient_email="", api_key="valid_token"
    )
    assert ok_no_rec is False
    assert "valid recipient email" in msg_no_rec

    # With api key and recipient email - success
    mock_resp = MagicMock(status_code=200, text='{"id": "test_msg_1"}')
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        ok_with_key, msg_with_key = await EmailNotificationAdapter.test_managed_connection(
            recipient_email="admin@company.com",
            api_key="valid_token",
            base_url="https://api.orbit.dev/v1/emails",
        )
        assert ok_with_key is True
        assert "successfully dispatched" in msg_with_key
        assert "admin@company.com" in msg_with_key

    # Error reporting test
    mock_err_resp = MagicMock(status_code=403, text='{"message": "domain not verified"}', json=lambda: {"message": "domain not verified"})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_err_resp
        ok_fail, msg_fail = await EmailNotificationAdapter.test_managed_connection(
            recipient_email="admin@company.com",
            api_key="valid_token",
            base_url="https://api.resend.com/emails",
        )
        assert ok_fail is False
        assert "authorization failed" in msg_fail.lower() or "verify" in msg_fail.lower()


def test_email_adapter_test_smtp_connection_missing_host():
    ok, msg = EmailNotificationAdapter.test_smtp_connection(host="")
    assert ok is False
    assert "SMTP Host is required" in msg
