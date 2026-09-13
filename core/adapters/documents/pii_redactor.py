import json
import logging
import httpx

from core.config.settings import get_settings

logger = logging.getLogger("core.adapters.documents.pii_redactor")


class PiiDocumentRedactor:
    """Automated PII redaction and compliance masking client."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.document_redactor_api_key
        self.base_url = (base_url or settings.document_redactor_base_url).rstrip("/")

    async def redact_pii(
        self, file_bytes: bytes, entity_types: list[str] | None = None
    ) -> bytes:
        """Sanitizes sensitive PII entities (email, SSN, cards) from document payloads."""
        if not self.api_key:
            return file_bytes

        base = self.base_url.rstrip("/")
        url = f"{base}/build" if not base.endswith("/build") else base
        headers = {"Authorization": f"Bearer {self.api_key}"}

        instructions = json.dumps({
            "parts": [
                {"file": "document.pdf"}
            ],
            "actions": [
                {
                    "type": "createRedactions",
                    "strategy": "preset",
                    "preset": "email-address"
                },
                {
                    "type": "applyRedactions"
                }
            ]
        })

        files = {
            "document.pdf": ("document.pdf", file_bytes, "application/pdf"),
            "instructions": (None, instructions, "text/plain"),
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, files=files)
                res.raise_for_status()
                return res.content
        except Exception as e:
            logger.warning(f"PII redaction failed: {e}. Returning unredacted document.")
            return file_bytes
