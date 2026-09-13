from typing import Any, Protocol


class DataSink(Protocol):
    """Protocol for exporting extracted records and dossiers to external storage."""

    async def export_results(
        self,
        automation_id: str,
        run_id: str,
        records: list[dict[str, Any]],
        dossier_bytes: bytes | None = None,
        dossier_filename: str | None = None,
    ) -> bool: ...


class NotificationAdapter(Protocol):
    """Protocol for external communication platforms."""

    async def send_alert(
        self,
        title: str,
        message: str,
        payload: dict[str, Any] | None = None,
        dossier_url: str | None = None,
    ) -> bool: ...


class DocumentParser(Protocol):
    """Protocol for parsing documents (PDF/DOCX) into LLM-ready markdown and structured tables."""

    async def parse_document(self, file_bytes: bytes, mime_type: str = "application/pdf") -> str: ...


class DocumentConverter(Protocol):
    """Protocol for format normalization, OCR, and document compression."""

    async def convert_to_pdf(self, file_bytes: bytes, source_format: str) -> bytes: ...
    async def run_ocr(self, file_bytes: bytes) -> bytes: ...
    async def compress_pdf(self, file_bytes: bytes) -> bytes: ...


class DocumentGenerator(Protocol):
    """Protocol for compiling structured extraction data into executive PDF dossiers."""

    async def generate_dossier(
        self,
        automation_id: str,
        run_id: str,
        records: list[dict[str, Any]],
        plan_summary: str | None = None,
        template_id: str | None = None,
        sources: list[str] | None = None,
    ) -> bytes: ...


class DocumentRedactor(Protocol):
    """Protocol for detecting and redacting sensitive PII entities."""

    async def redact_pii(self, file_bytes: bytes, entity_types: list[str] | None = None) -> bytes: ...
