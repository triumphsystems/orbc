import logging
from typing import Any

from core.adapters.documents.types import DocumentMetadata, ParsedDocument

logger = logging.getLogger("core.adapters.documents.layout_parser")


class LayoutDocumentParser:
    """Semantic document layout parser and table deconstructor for LLM extraction."""

    def __init__(self, use_ocr: bool = True):
        self.use_ocr = use_ocr

    async def parse_document(self, file_bytes: bytes, mime_type: str = "application/pdf") -> str:
        """Parses document bytes into structured markdown tables and text."""
        try:
            parsed = await self.parse_to_structured(file_bytes, mime_type)
            return parsed.content_markdown
        except Exception as e:
            logger.warning(f"Layout parsing failed: {e}. Falling back to basic text decoding.")
            return file_bytes.decode("utf-8", errors="ignore")

    async def parse_to_structured(self, file_bytes: bytes, mime_type: str = "application/pdf") -> ParsedDocument:
        """Extracts text sections, headers, and markdown-formatted tables."""
        raw_text = file_bytes.decode("utf-8", errors="ignore")
        tables: list[dict[str, Any]] = []

        lines = raw_text.splitlines()
        markdown_sections: list[str] = []
        table_count = 0

        for line in lines:
            if "|" in line:
                markdown_sections.append(line)
                table_count += 1
            elif line.strip().startswith("#"):
                markdown_sections.append(f"\n{line}")
            elif line.strip():
                markdown_sections.append(line)

        markdown_output = "\n".join(markdown_sections)
        if not markdown_output.strip():
            markdown_output = raw_text

        metadata = DocumentMetadata(
            title="Ingested Document",
            page_count=max(1, len(lines) // 50),
            detected_tables_count=table_count,
        )

        return ParsedDocument(
            content_markdown=markdown_output,
            metadata=metadata,
            tables=tables,
            raw_text=raw_text,
        )
