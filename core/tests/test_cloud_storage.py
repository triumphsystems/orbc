import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from core.adapters.storage.cloud_storage import CloudStorageSink


@pytest.mark.asyncio
async def test_cloud_storage_local_export():
    sink = CloudStorageSink(backend="local")
    records = [{"title": "Widget Alpha", "price": 99.99}]
    dossier = b"PDF Briefing Bytes"

    success = await sink.export_results(
        automation_id="auto-test-111",
        run_id="run-test-222",
        records=records,
        dossier_bytes=dossier,
        dossier_filename="report.pdf",
    )
    assert success is True

    # Verify local file creation
    record_file = Path("exports/auto-tes/run-test/records.json")
    pdf_file = Path("exports/auto-tes/run-test/report.pdf")
    assert record_file.exists()
    assert pdf_file.exists()

    # Clean up test artifacts
    if record_file.exists():
        record_file.unlink()
    if pdf_file.exists():
        pdf_file.unlink()


@pytest.mark.asyncio
async def test_cloud_storage_gcs_upload():
    sink = CloudStorageSink(
        backend="gcs",
        bucket_name="orbit-production-bucket",
        access_key="mock-gcp-token",
    )

    mock_res = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_res
        url = await sink.upload_file("reports/test.pdf", b"%PDF-1.4", "application/pdf")
        assert "storage.googleapis.com/orbit-production-bucket/reports/test.pdf" in url
        assert mock_post.called


@pytest.mark.asyncio
async def test_cloud_storage_s3_upload():
    sink = CloudStorageSink(
        backend="s3",
        bucket_name="orbit-s3-bucket",
        region="us-east-1",
        access_key="AKIA123",
        secret_key="secret456",
    )

    mock_res = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.put", new_callable=AsyncMock) as mock_put:
        mock_put.return_value = mock_res
        url = await sink.upload_file("exports/data.json", b"{}", "application/json")
        assert "orbit-s3-bucket" in url
        assert mock_put.called


@pytest.mark.asyncio
async def test_cloud_storage_connection_probes():
    # Local probe
    local_sink = CloudStorageSink(backend="local")
    ok, msg = await local_sink.test_connection()
    assert ok is True

    # GCS probe with mock
    gcs_sink = CloudStorageSink(backend="gcs", bucket_name="test-gcs-bucket")
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head:
        mock_head.return_value = MagicMock(status_code=200)
        ok, msg = await gcs_sink.test_connection()
        assert ok is True
        assert "Google Cloud Storage" in msg
