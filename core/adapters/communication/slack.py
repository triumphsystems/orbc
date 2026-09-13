import logging
from typing import Any
import httpx

logger = logging.getLogger("core.adapters.communication.slack")


class SlackWebhookAdapter:
    """Dispatches alerts formatted as Slack blocks with metrics and dossier download links."""

    webhook_url: str

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_alert(
        self,
        title: str,
        message: str,
        payload: dict[str, Any] | None = None,
        dossier_url: str | None = None,
    ) -> bool:
        if not self.webhook_url:
            return False

        blocks: list[dict[str, Any]] = [
            {"type": "header", "text": {"type": "plain_text", "text": f"🛰️ {title}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*{message}*"}},
        ]

        if payload:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Telemetry: `{payload}`"}],
            })

        if dossier_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📄 Download Intelligence Dossier"},
                        "url": dossier_url,
                        "style": "primary",
                    }
                ],
            })

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.webhook_url, json={"blocks": blocks})
                return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    async def test_connection(self) -> tuple[bool, str]:
        """Tests live reachability of the Slack Incoming Webhook endpoint with a test diagnostic card."""
        if not self.webhook_url:
            return False, "Slack Webhook URL is not configured."
        if not (self.webhook_url.startswith("https://hooks.slack.com/") or self.webhook_url.startswith("https://") or self.webhook_url.startswith("http://")):
            return False, "Invalid Slack Webhook URL. It must be a valid webhook endpoint (e.g. https://hooks.slack.com/services/...)."

        test_blocks: list[dict[str, Any]] = [
            {"type": "header", "text": {"type": "plain_text", "text": "🛰️ Orbit Connection Probe"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Slack Incoming Webhook verified successfully.*\nOrbit notification alerts are ready to dispatch to this channel."}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "Status: `operational` | Diagnostic: `orbit.slack.probe`"}]},
        ]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.webhook_url, json={"blocks": test_blocks})
                if resp.status_code == 200:
                    return True, "Slack webhook probe verified and test card dispatched to channel."
                if resp.status_code == 404:
                    return False, "Slack webhook returned 404 Not Found (channel or webhook token may be invalid)."
                if resp.status_code == 403:
                    return False, "Slack webhook returned 403 Forbidden (webhook may be revoked or inactive)."
                logger.error("Slack webhook returned HTTP %s: %s", resp.status_code, resp.text)
                return False, f"Slack webhook returned HTTP {resp.status_code}. Please verify the webhook configuration."
        except Exception as e:
            logger.error("Slack webhook probe failed: %s", e)
            return False, "Could not reach Slack webhook endpoint. Please verify your internet connection and webhook URL."
