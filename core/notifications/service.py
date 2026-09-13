import logging
from typing import Any

from core.adapters.communication.email import EmailNotificationAdapter
from core.adapters.communication.slack import SlackWebhookAdapter
from core.adapters.communication.webhook import SignedWebhookAdapter
from core.config.settings import get_settings

logger = logging.getLogger("core.notifications")


class NotificationService:
    """Dispatches alerts via managed or custom provider-agnostic email, signed webhook, or Slack adapters."""

    def __init__(self):
        self.settings = get_settings()
        self.email_adapter = EmailNotificationAdapter()

    async def notify(
        self,
        title: str,
        message: str,
        payload: dict[str, Any] | None = None,
        webhook_url: str | None = None,
        dossier_url: str | None = None,
        recipient_email: str | None = None,
        channel: str | None = None,
    ) -> bool:
        """Routes notification alert to designated communication sink (email, slack, webhook)."""
        logger.info(f"🔔 [ORBIT ALERT] {title}: {message}")
        target_url = webhook_url
        target_email = recipient_email
        success = True

        # Route to Provider-Agnostic Email if requested or recipient configured
        if channel == "email" or target_email or (target_url and "@" in target_url and not target_url.startswith("http")):
            effective_recipient = target_email or (target_url if target_url and "@" in target_url else None)
            if effective_recipient:
                email_sent = await self.email_adapter.send_alert(
                    title=title,
                    message=message,
                    recipient_email=effective_recipient,
                    payload=payload,
                    dossier_url=dossier_url,
                )
                if channel == "email":
                    return email_sent
                success = success and email_sent

        if not target_url or not target_url.startswith("http"):
            return success

        # Route to Slack if URL is Slack webhook
        if "hooks.slack.com" in target_url or channel == "slack":
            slack_adapter = SlackWebhookAdapter(webhook_url=target_url)
            slack_sent = await slack_adapter.send_alert(title, message, payload=payload, dossier_url=dossier_url)
            return success and slack_sent

        # Route to HMAC-Signed Webhook for general HTTP endpoints
        signed_adapter = SignedWebhookAdapter(webhook_url=target_url)
        webhook_sent = await signed_adapter.send_alert(title, message, payload=payload, dossier_url=dossier_url)
        return success and webhook_sent
