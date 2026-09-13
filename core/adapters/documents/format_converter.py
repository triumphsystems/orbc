import logging
import httpx

from core.config.settings import get_settings

logger = logging.getLogger("core.adapters.documents.format_converter")


class FormatDocumentConverter:
    """Document transformation client for format normalization, OCR, and compression."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.document_converter_api_key
        self.base_url = (base_url or settings.document_converter_base_url).rstrip("/")

    async def convert_to_pdf(self, file_bytes: bytes, source_format: str = "docx") -> bytes:
        """Converts Office/image files to standardized PDF/A."""
        if not self.api_key:
            return file_bytes

        url = f"{self.base_url}/conversion/to-pdf"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/octet-stream"}
        params = {"source_format": source_format, "pdf_standard": "PDF/A"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, params=params, content=file_bytes)
                res.raise_for_status()
                return res.content
        except Exception as e:
            logger.warning(f"Format conversion failed: {e}. Returning original bytes.")
            return file_bytes

    async def run_ocr(self, file_bytes: bytes) -> bytes:
        """Executes OCR on scanned document pages."""
        if not self.api_key:
            return file_bytes

        url = f"{self.base_url}/ocr/process"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/octet-stream"}
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, headers=headers, content=file_bytes)
                res.raise_for_status()
                return res.content
        except Exception as e:
            logger.warning(f"OCR processing failed: {e}. Continuing with original bytes.")
            return file_bytes

    async def compress_pdf(self, file_bytes: bytes) -> bytes:
        """Compresses and linearizes PDF files before archive storage."""
        if not self.api_key:
            return file_bytes

        url = f"{self.base_url}/optimizer/compress"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/octet-stream"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, headers=headers, content=file_bytes)
                res.raise_for_status()
                return res.content
        except Exception as e:
            logger.warning(f"Document compression failed: {e}. Returning uncompressed bytes.")
            return file_bytes
