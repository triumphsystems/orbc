import asyncio
import html
import logging
from typing import Any
import httpx

from core.config.settings import get_settings

logger = logging.getLogger("core.adapters.communication.email")


class EmailNotificationAdapter:
    """Provider-agnostic transactional email adapter supporting managed and custom delivery."""

    @classmethod
    async def test_managed_connection(
        cls,
        recipient_email: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        sender_address: str | None = None,
    ) -> tuple[bool, str]:
        """Tests connection and credentials for the managed outbound email gateway by sending a test email."""
        settings = get_settings()
        key = (api_key or settings.email_api_key or "").strip().strip("'\"")
        url = (base_url or settings.email_base_url or "https://api.orbit.dev/v1/emails").strip().strip("'\"")
        sender = (sender_address or settings.email_sender_address or "Orbit Alerts <alerts@orbit.dev>").strip().strip("'\"")

        if not key:
            return False, "Managed Email API Key is not configured on daemon (missing EMAIL_API_KEY in .env)."

        recipient = str(recipient_email or "").strip().strip("'\"")
        if not recipient or "@" not in recipient:
            return False, "A valid recipient email address is required (e.g. team@company.com)."

        adapter = cls(api_key=key, sender_address=sender, base_url=url, max_retries=1)
        subject = "🛰️ [Orbit Probe] Test Email Notification"
        html_body = adapter._render_html_template(
            title="Connection Probe Verified",
            message="This is a test notification dispatched by Orbit to verify that your managed transactional email adapter is functioning correctly.",
            payload={"gateway_status": "operational", "recipient": recipient},
        )
        text_body = adapter._render_text_template(
            title="Connection Probe Verified",
            message="This is a test notification dispatched by Orbit to verify that your managed transactional email adapter is functioning correctly.",
            payload={"gateway_status": "operational", "recipient": recipient},
        )

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Orbit-Email-Adapter/1.0",
        }
        payload: dict[str, Any] = {
            "from": sender,
            "to": [recipient],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code in (200, 201, 202):
                    logger.info("Test probe email dispatched successfully to %s", recipient)
                    return True, f"Test probe email successfully dispatched to '{recipient}'."

                logger.error(
                    "Managed email delivery failed [%s]: %s (sender: %s, url: %s)",
                    resp.status_code,
                    resp.text,
                    sender,
                    url,
                )

                if resp.status_code in (401, 403):
                    return False, "Email gateway authorization failed. Please check your EMAIL_API_KEY and verified sender address."
                if resp.status_code == 422:
                    return False, "Email gateway rejected the recipient or sender address format. Please verify your email settings."
                return False, f"Email gateway returned HTTP {resp.status_code}. Please verify outbound email configuration."

        except httpx.ConnectError as ce:
            logger.error("Email gateway connection error: %s (url: %s)", ce, url)
            return False, "Unable to reach the outbound email gateway. Please check your network connection and gateway endpoint."
        except httpx.TimeoutException:
            logger.error("Email gateway request timed out (url: %s)", url)
            return False, "Email gateway request timed out. Please check gateway reachability and retry."
        except Exception as e:
            logger.exception("Unexpected error during email probe: %s", e)
            return False, "An error occurred while connecting to the email gateway. Please check your configuration."

    @staticmethod
    def test_smtp_connection(
        host: str,
        port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
    ) -> tuple[bool, str]:
        """Tests connection to a custom SMTP server."""
        import smtplib
        import ssl

        if not host:
            return False, "SMTP Host is required for custom email delivery."

        try:
            if port == 465 or (not use_tls and port != 587):
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as server:
                    if username and password:
                        server.login(username, password)
                    return True, f"SMTP server '{host}:{port}' connected and authenticated successfully."
            else:
                with smtplib.SMTP(host, port, timeout=10) as server:
                    if use_tls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    if username and password:
                        server.login(username, password)
                    return True, f"SMTP server '{host}:{port}' connected and authenticated successfully."
        except Exception as e:
            logger.error("SMTP connection error: %s", e)
            return False, "Could not establish connection to the SMTP server. Please verify the host, port, and credentials."

    def __init__(
        self,
        api_key: str | None = None,
        sender_address: str | None = None,
        base_url: str | None = None,
        mode: str = "both",
        max_retries: int = 3,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.email_api_key or ""
        self.sender_address = sender_address or settings.email_sender_address or "Orbit Alerts <alerts@orbit.dev>"
        self.base_url = base_url or settings.email_base_url or "https://api.orbit.dev/v1/emails"
        self.mode = mode
        self.max_retries = max_retries

    async def send_email(
        self,
        to: list[str] | str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        custom_api_key: str | None = None,
        custom_sender: str | None = None,
        custom_base_url: str | None = None,
    ) -> bool:
        """Sends an outbound transactional email with authorization headers and exponential backoff retries.
        
        Supports managed mode (platform credentials) and custom mode (overridden credentials).
        """
        active_api_key = custom_api_key or self.api_key
        active_sender = custom_sender or self.sender_address
        active_url = custom_base_url or self.base_url

        if not active_api_key:
            logger.warning("Email dispatch skipped: EMAIL_API_KEY is not configured (neither managed nor custom).")
            return False

        recipients = [to] if isinstance(to, str) else to
        if not recipients:
            logger.warning("Email dispatch skipped: No recipient specified.")
            return False

        headers = {
            "Authorization": f"Bearer {active_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Orbit-Email-Adapter/1.0",
        }

        payload: dict[str, Any] = {
            "from": active_sender,
            "to": recipients,
            "subject": subject,
            "html": html_body,
        }
        if text_body:
            payload["text"] = text_body

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(active_url, headers=headers, json=payload)
                    if resp.status_code in (200, 201, 202):
                        logger.info(f"Email successfully delivered to {recipients} (status: HTTP {resp.status_code})")
                        return True

                    logger.warning(
                        f"Email delivery attempt {attempt} failed with HTTP {resp.status_code}: {resp.text}"
                    )
            except Exception as e:
                logger.warning(f"Email delivery attempt {attempt} encountered error: {e}")

            if attempt < self.max_retries:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

        logger.error(f"Email delivery failed permanently after {self.max_retries} attempts.")
        return False

    async def send_alert(
        self,
        title: str,
        message: str,
        recipient_email: str | None = None,
        payload: dict[str, Any] | None = None,
        dossier_url: str | None = None,
        custom_api_key: str | None = None,
        custom_sender: str | None = None,
        custom_base_url: str | None = None,
    ) -> bool:
        """Renders an alert template and delivers via managed or custom transactional email."""
        if not recipient_email:
            logger.warning("Email alert skipped: No recipient email address specified.")
            return False

        subject = f"🛰️ [Orbit Alert] {title}"
        html_content = self._render_html_template(title, message, payload=payload, dossier_url=dossier_url)
        text_content = self._render_text_template(title, message, payload=payload, dossier_url=dossier_url)

        return await self.send_email(
            to=recipient_email,
            subject=subject,
            html_body=html_content,
            text_body=text_content,
            custom_api_key=custom_api_key,
            custom_sender=custom_sender,
            custom_base_url=custom_base_url,
        )

    def _render_html_template(
        self,
        title: str,
        message: str,
        payload: dict[str, Any] | None = None,
        dossier_url: str | None = None,
    ) -> str:
        """Generates a responsive HTML email matching Orbit's modern dark theme."""
        escaped_title = html.escape(title)
        escaped_msg = html.escape(message)

        dossier_button = ""
        if dossier_url:
            dossier_button = f"""
            <div style="margin: 28px 0; text-align: center;">
                <a href="{html.escape(dossier_url)}" style="background-color: #06b6d4; color: #020617; font-weight: 600; font-size: 14px; text-decoration: none; padding: 12px 24px; border-radius: 8px; display: inline-block; box-shadow: 0 4px 12px rgba(6, 182, 212, 0.25);">
                    📄 Download Intelligence Dossier
                </a>
            </div>
            """

        telemetry_block = ""
        if payload:
            rows = ""
            for k, v in payload.items():
                if k == "dossier_url":
                    continue
                rows += f"""
                <tr>
                    <td style="padding: 8px 12px; font-family: monospace; font-size: 12px; color: #94a3b8; border-bottom: 1px solid #334155;">{html.escape(str(k))}</td>
                    <td style="padding: 8px 12px; font-family: monospace; font-size: 12px; color: #f8fafc; border-bottom: 1px solid #334155; text-align: right;">{html.escape(str(v))}</td>
                </tr>
                """
            if rows:
                telemetry_block = f"""
                <div style="margin-top: 24px; background-color: #0b1329; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden;">
                    <div style="padding: 10px 14px; background-color: #0f172a; border-bottom: 1px solid #1e293b; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #38bdf8;">
                        Mission Telemetry
                    </div>
                    <table style="width: 100%; border-collapse: collapse;">
                        {rows}
                    </table>
                </div>
                """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escaped_title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #020617; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0; line-height: 1.6;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 32px 16px; text-align: center;">
                <table role="presentation" style="max-width: 580px; width: 100%; margin: 0 auto; background-color: #090e1a; border: 1px solid #1e293b; border-radius: 12px; overflow: hidden; text-align: left; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 24px 32px; background-color: #0b132b; border-bottom: 1px solid #1e293b;">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-size: 16px; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em;">🛰️ ORBIT</span>
                                <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; background-color: rgba(6, 182, 212, 0.15); color: #22d3ee; padding: 4px 10px; border-radius: 9999px; border: 1px solid rgba(6, 182, 212, 0.3);">
                                    Condition Alert
                                </span>
                            </div>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 32px;">
                            <h1 style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #f8fafc; line-height: 1.4;">
                                {escaped_title}
                            </h1>
                            <p style="margin: 0 0 20px 0; font-size: 14px; color: #cbd5e1; line-height: 1.6; background-color: #0f172a; border-left: 3px solid #06b6d4; padding: 14px 16px; border-radius: 4px;">
                                {escaped_msg}
                            </p>

                            {dossier_button}
                            {telemetry_block}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 32px; background-color: #050b14; border-top: 1px solid #1e293b; font-size: 12px; color: #64748b; text-align: center;">
                            Automated notification dispatched by Orbit Autonomous Data Operations.<br>
                            To adjust trigger conditions or sinks, configure your mission parameters in Orbit.
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def _render_text_template(
        self,
        title: str,
        message: str,
        payload: dict[str, Any] | None = None,
        dossier_url: str | None = None,
    ) -> str:
        """Generates plain text alternative for fallback email clients."""
        text = f"🛰️ ORBIT ALERT: {title}\n\n"
        text += f"{message}\n\n"
        if dossier_url:
            text += f"Download Intelligence Dossier:\n{dossier_url}\n\n"
        if payload:
            text += "Telemetry:\n"
            for k, v in payload.items():
                if k != "dossier_url":
                    text += f"- {k}: {v}\n"
        text += "\n---\nOrbit Autonomous Data Operations"
        return text
