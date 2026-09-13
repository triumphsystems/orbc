import logging
from core.adapters.documents.types import DocumentMetadata, ParsedDocument

logger = logging.getLogger("core.adapters.documents.plain_parser")


class PlainDocumentParser:
    """Lightweight plain text parser for basic document decoding."""

    async def parse_document(self, file_bytes: bytes, mime_type: str = "application/pdf") -> str:
        """Parses document bytes into plain text."""
        return file_bytes.decode("utf-8", errors="ignore")

    async def parse_to_structured(self, file_bytes: bytes, mime_type: str = "application/pdf") -> ParsedDocument:
        """Decodes raw text and extracts basic lines and sections."""
        text = file_bytes.decode("utf-8", errors="ignore")
        lines = text.splitlines()

        metadata = DocumentMetadata(
            title="Plain Document",
            page_count=max(1, len(lines) // 40),
            detected_tables_count=sum(1 for line in lines if "|" in line),
        )

        return ParsedDocument(
            content_markdown=text,
            metadata=metadata,
            tables=[],
            raw_text=text,
        )
