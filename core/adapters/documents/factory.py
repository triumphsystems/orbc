from core.adapters.base import DocumentConverter, DocumentGenerator, DocumentParser, DocumentRedactor
from core.adapters.documents.format_converter import FormatDocumentConverter
from core.adapters.documents.html_generator import HtmlDossierGenerator
from core.adapters.documents.layout_parser import LayoutDocumentParser
from core.adapters.documents.pii_redactor import PiiDocumentRedactor
from core.adapters.documents.plain_parser import PlainDocumentParser
from core.adapters.documents.template_generator import TemplateDossierGenerator
from core.adapters.documents.text_generator import TextDossierGenerator
from core.config.settings import get_settings


class DocumentAdapterFactory:
    """Factory for document parsers, converters, generators, and redactors."""

    @staticmethod
    def get_parser() -> DocumentParser:
        """Returns the primary layout parser with plain text fallback."""
        try:
            return LayoutDocumentParser()
        except Exception:
            return PlainDocumentParser()

    @staticmethod
    def get_converter() -> DocumentConverter:
        """Returns document format transformation converter."""
        return FormatDocumentConverter()

    @staticmethod
    def get_generator(style: str = "html") -> DocumentGenerator:
        """Returns dossier generator (html, template, or text)."""
        settings = get_settings()
        if style == "template" and settings.document_template_api_key:
            return TemplateDossierGenerator()
        if style == "html" and settings.document_dossier_api_key:
            return HtmlDossierGenerator()
        if settings.document_dossier_api_key:
            return HtmlDossierGenerator()
        if settings.document_template_api_key:
            return TemplateDossierGenerator()
        return TextDossierGenerator()

    @staticmethod
    def get_redactor() -> DocumentRedactor:
        """Returns PII redaction engine."""
        return PiiDocumentRedactor()
