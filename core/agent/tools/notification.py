import logging
from typing import Any
from strands import tool

logger = logging.getLogger("core.agent.tools.notification")


@tool
async def send_mission_alert(
    channel: str,
    target: str,
    subject: str,
    message: str,
    data_payload: dict[str, Any] = {},
) -> dict[str, Any]:
    """
    Sends execution alerts and notifications over Slack, Email, or Webhooks.

    Args:
        channel: Notification channel ('email', 'slack', 'webhook').
        target: Target recipient (email address, Slack webhook URL, HTTP endpoint).
        subject: Alert subject or summary title.
        message: Detailed notification message body.
        data_payload: Optional structured records or payload metadata to include.
    """
    logger.info("Strands tool send_mission_alert: channel='%s' target='%s'", channel, target)
    from core.adapters.communication.notification import NotificationService

    service = NotificationService()
    try:
        success = await service.send_alert(
            channel=channel,
            target=target,
            subject=subject,
            message=message,
            payload=data_payload,
        )
        return {"status": "success" if success else "failed", "channel": channel}
    except Exception as e:
        logger.warning("Failed sending mission alert: %s", e)
        return {"status": "error", "message": str(e)}
