import json
import pytest

from core.adapters.documents.factory import DocumentAdapterFactory
from core.adapters.documents.html_generator import HtmlDossierGenerator
from core.adapters.documents.pii_redactor import PiiDocumentRedactor
from core.adapters.documents.template_generator import TemplateDossierGenerator
from core.adapters.documents.text_generator import TextDossierGenerator


@pytest.mark.asyncio
async def test_html_dossier_generator_template():
    generator = HtmlDossierGenerator(api_key="")
    records = [{"url": "https://data.com/1", "data": {"price": 120, "title": "Widget A"}}]
    dossier_bytes = await generator.generate_dossier("auto-123", "run-456", records, plan_summary="Scrape Widgets")
    html_text = dossier_bytes.decode("utf-8")
    assert "Orbit Mission Intelligence Dossier" in html_text
    assert "Widget A" in html_text
    assert "auto-123" in html_text


@pytest.mark.asyncio
async def test_template_dossier_generator_offline_payload():
    generator = TemplateDossierGenerator(api_key="")
    records = [{"data": {"metric": "CPU", "usage": "88%"}}]
    payload_bytes = await generator.generate_dossier("auto-999", "run-888", records)
    payload = json.loads(payload_bytes.decode("utf-8"))
    assert payload["automation_id"] == "auto-999"
    assert payload["record_count"] == 1


@pytest.mark.asyncio
async def test_pii_redactor_offline_passthrough():
    redactor = PiiDocumentRedactor(api_key="")
    sample_doc = b"Confidential Report with test@example.com"
    result = await redactor.redact_pii(sample_doc)
    assert result == sample_doc


@pytest.mark.asyncio
async def test_text_dossier_generator():
    generator = TextDossierGenerator()
    records = [{"url": "https://source.com", "data": {"status": "ok"}}]
    briefing = await generator.generate_dossier("auto-1", "run-1", records, plan_summary="Status Check")
    text = briefing.decode("utf-8")
    assert "# Orbit Intelligence Dossier" in text
    assert "Status Check" in text
    assert "https://source.com" in text


@pytest.mark.asyncio
async def test_template_dossier_generator_doctavian_flow():
    from unittest.mock import AsyncMock, MagicMock, patch

    generator = TemplateDossierGenerator(api_key="mock-doctavian-key", base_url="https://api.doctavian.com/v1")
    records = [{"data": {"invoice_id": "INV-101", "total": "$500"}}]

    # Mock response 1: Upload JSON data
    mock_upload_res = MagicMock(status_code=201)
    mock_upload_res.json.return_value = {
        "result": {"data": {"files": [{"id": "data-guid-12345", "fileName": "data.json"}]}},
        "statusCode": 201,
    }

    # Mock response 2: Generate Document
    mock_gen_res = MagicMock(status_code=200, headers={"content-type": "application/json"})
    mock_gen_res.json.return_value = {
        "result": {"data": {"document": {"id": "doc-guid-99999", "name": "Orbit-Report"}}},
        "statusCode": 200,
    }

    # Mock response 3: Download Document
    mock_dl_res = MagicMock(status_code=200, content=b"%PDF-1.4 Mocked Doctavian PDF Output")
    mock_dl_res.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_post.side_effect = [mock_upload_res, mock_gen_res]
        mock_get.return_value = mock_dl_res

        result_pdf = await generator.generate_dossier(
            automation_id="auto-555",
            run_id="run-777",
            records=records,
            template_id="template-contract-v1",
        )

        assert result_pdf == b"%PDF-1.4 Mocked Doctavian PDF Output"
        assert mock_post.call_count == 2
        assert mock_get.call_count == 1
