from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DocumentMetadata:
    """Metadata extracted from document headers and structural layout."""

    title: str | None = None
    author: str | None = None
    page_count: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    detected_tables_count: int = 0
    language: str = "en"


@dataclass
class ParsedDocument:
    """Structured result of inbound document parsing with layout and table awareness."""

    content_markdown: str
    metadata: DocumentMetadata
    tables: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class DossierPayload:
    """Payload data used by document and dossier generators to compile briefings."""

    automation_id: str
    run_id: str
    objective: str
    domain: str
    records: list[dict[str, Any]]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    template_id: str | None = None
