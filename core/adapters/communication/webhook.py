import asyncio
from datetime import date, datetime
from decimal import Decimal
import hashlib
import hmac
import json
import logging
import time
from typing import Any
import uuid
import httpx

from core.config.settings import get_settings
from core.utils.security import validate_url_target

logger = logging.getLogger("core.adapters.communication.webhook")


def _json_serial(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


class WebhookAdapter:
    """Provider-agnostic outbound webhook adapter supporting HMAC-SHA256 signatures, custom headers, and retries."""

    def __init__(
        self,
        webhook_url: str | None = None,
        signing_secret: str | None = None,
        custom_headers: dict[str, str] | None = None,
        signature_header: str = "X-Orbit-Signature",
        timeout_sec: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        settings = get_settings()
        self.webhook_url = webhook_url or ""
        self.signing_secret = signing_secret or settings.orbit_secret_key
        self.custom_headers = custom_headers or {}
        self.signature_header = signature_header
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _sign_payload(self, timestamp: int, payload_json: str) -> str:
        """Generates standard HMAC-SHA256 signature in t={timestamp},v1={hash} format."""
        signature_payload = f"t={timestamp}.{payload_json}".encode("utf-8")
        computed = hmac.new(self.signing_secret.encode("utf-8"), signature_payload, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={computed}"

    async def send_event(
        self,
        event_type: str,
        data: dict[str, Any],
        custom_headers: dict[str, str] | None = None,
        target_url: str | None = None,
    ) -> bool:
        """Sends an event payload with standard headers, HMAC signature, and exponential backoff."""
        url = target_url or self.webhook_url
        if not url:
            logger.warning("Webhook dispatch skipped: No webhook URL configured.")
            return False

        # SSRF Protection
        settings = get_settings()
        allow_private = settings.app_env.lower() not in ("production", "prod", "staging")
        is_safe, reason = validate_url_target(url, allow_private=allow_private)
        if not is_safe:
            logger.warning("Webhook dispatch blocked by SSRF protection: %s (%s)", url, reason)
            return False

        timestamp = int(time.time())
        delivery_id = str(uuid.uuid4())
        body_dict = {
            "event": event_type,
            "timestamp": timestamp,
            "delivery_id": delivery_id,
            "data": data,
        }
        body_json = json.dumps(body_dict, default=_json_serial)
        signature = self._sign_payload(timestamp, body_json)

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "Orbit-Webhook-Emitter/1.0",
            self.signature_header: signature,
            "X-Orbit-Signature": signature,
            "X-Orbit-Timestamp": str(timestamp),
            "X-Orbit-Event": event_type,
            "X-Orbit-Delivery-Id": delivery_id,
        }
        # Merge adapter-level and per-call custom headers
        if self.custom_headers:
            headers.update(self.custom_headers)
        if custom_headers:
            headers.update(custom_headers)

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                    resp = await client.post(url, headers=headers, content=body_json)
                    if resp.status_code in (200, 201, 202, 204):
                        logger.info(
                            f"Webhook event '{event_type}' delivered successfully to {url} (status: HTTP {resp.status_code})"
                        )
                        return True
                    logger.warning(
                        f"Webhook delivery attempt {attempt} to {url} returned HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                logger.warning(f"Webhook delivery attempt {attempt} to {url} encountered error: {e}")

            if attempt < self.max_retries:
                await asyncio.sleep(self.backoff_factor * (2 ** (attempt - 1)))

        logger.error(f"Webhook event '{event_type}' delivery failed permanently after {self.max_retries} attempts.")
        return False

    async def send_alert(
        self,
        title: str,
        message: str,
        payload: dict[str, Any] | None = None,
        dossier_url: str | None = None,
    ) -> bool:
        """Dispatches an alert.condition_matched webhook event."""
        data = {
            "title": title,
            "message": message,
            "payload": payload or {},
            "dossier_url": dossier_url,
        }
        return await self.send_event("alert.condition_matched", data)

    async def send_records(
        self,
        automation_id: str,
        run_id: str,
        records: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Dispatches extracted records batch via data.records_extracted webhook event."""
        data = {
            "automation_id": automation_id,
            "run_id": run_id,
            "records_count": len(records),
            "records": records,
            "metadata": metadata or {},
        }
        return await self.send_event("data.records_extracted", data)

    async def test_connection(self, probe_url: str | None = None) -> tuple[bool, str]:
        """Probes the webhook destination with an orbit.ping diagnostic payload."""
        url = probe_url or self.webhook_url
        if not url:
            return False, "Webhook URL is not configured."

        from datetime import timezone
        ping_data = {"diagnostic": "connectivity_probe", "sent_at": datetime.now(timezone.utc).isoformat()}
        success = await self.send_event("orbit.ping", ping_data, target_url=url)
        if success:
            return True, f"Webhook endpoint '{url}' reached and acknowledged successfully."
        return False, f"Webhook endpoint '{url}' failed to acknowledge probe request."

    @staticmethod
    def verify_signature(
        payload_bytes: bytes,
        signature_header: str,
        secret: str,
        tolerance_sec: int = 300,
    ) -> bool:
        """Verifies signature header against secret key preventing replay and tampering attacks."""
        try:
            parts = dict(part.split("=", 1) for part in signature_header.split(","))
            timestamp = int(parts.get("t", 0))
            received_sig = parts.get("v1", "")

            if tolerance_sec > 0 and abs(time.time() - timestamp) > tolerance_sec:
                return False

            payload_json = payload_bytes.decode("utf-8")
            signature_payload = f"t={timestamp}.{payload_json}".encode("utf-8")
            expected_sig = hmac.new(secret.encode("utf-8"), signature_payload, hashlib.sha256).hexdigest()
            return hmac.compare_digest(received_sig, expected_sig)
        except Exception:
            return False


# Backward compatibility alias
SignedWebhookAdapter = WebhookAdapter

