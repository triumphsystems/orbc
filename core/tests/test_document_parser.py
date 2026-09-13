import pytest

from core.adapters.documents.factory import DocumentAdapterFactory
from core.adapters.documents.format_converter import FormatDocumentConverter
from core.adapters.documents.layout_parser import LayoutDocumentParser
from core.adapters.documents.plain_parser import PlainDocumentParser


@pytest.mark.asyncio
async def test_layout_parser_table_extraction():
    parser = LayoutDocumentParser()
    sample_doc = b"""# Financial Summary
| Quarter | Revenue | Profit |
|---|---|---|
| Q1 2026 | $12M | $3.2M |
| Q2 2026 | $15M | $4.1M |

Overview notes for stakeholders.
"""
    parsed = await parser.parse_to_structured(sample_doc, "application/pdf")
    assert parsed.metadata.detected_tables_count >= 1
    assert "Q1 2026" in parsed.content_markdown
    assert "Revenue" in parsed.content_markdown


@pytest.mark.asyncio
async def test_plain_parser_fallback():
    parser = PlainDocumentParser()
    sample_doc = b"Raw text document without markdown tables."
    parsed = await parser.parse_to_structured(sample_doc)
    assert parsed.metadata.title == "Plain Document"
    assert "Raw text document" in parsed.content_markdown


@pytest.mark.asyncio
async def test_format_converter_offline_passthrough():
    converter = FormatDocumentConverter(api_key="")
    raw_docx = b"PK\x03\x04...mock docx stream..."
    result = await converter.convert_to_pdf(raw_docx, source_format="docx")
    assert result == raw_docx

    compressed = await converter.compress_pdf(result)
    assert compressed == raw_docx


def test_factory_returns_active_parser():
    parser = DocumentAdapterFactory.get_parser()
    assert hasattr(parser, "parse_document")
