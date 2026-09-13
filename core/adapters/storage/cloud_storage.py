import json
import logging
import os
from pathlib import Path
from typing import Any
import httpx

from core.config.settings import get_settings
from core.utils.security import sign_s3_request

logger = logging.getLogger("core.adapters.storage.cloud_storage")


class CloudStorageSink:
    """Provider-agnostic unified cloud object storage export sink (GCS, S3, MinIO, Local)."""

    def __init__(
        self,
        backend: str | None = None,
        bucket_name: str | None = None,
        region: str | None = None,
        project_id: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
    ):
        settings = get_settings()
        self.backend = (backend or settings.storage_backend or "local").lower()
        self.bucket_name = bucket_name or settings.storage_bucket_name or "orbit-exports"
        self.region = region or settings.storage_region or "us-central1"
        self.project_id = project_id or settings.storage_project_id or ""
        self.access_key = access_key or settings.storage_access_key or ""
        self.secret_key = secret_key or settings.storage_secret_key or ""
        self.endpoint_url = endpoint_url or settings.storage_endpoint_url or ""

    async def export_results(
        self,
        automation_id: str,
        run_id: str,
        records: list[dict[str, Any]],
        dossier_bytes: bytes | None = None,
        dossier_filename: str | None = None,
    ) -> bool:
        """Uploads JSON records and compiled PDF dossiers into cloud object storage."""
        prefix = f"{automation_id[:8]}/{run_id[:8]}"
        json_key = f"{prefix}/records.json"

        try:
            # 1. Upload extracted JSON records
            json_bytes = json.dumps(records, indent=2, default=str).encode("utf-8")
            await self.upload_file(json_key, json_bytes, "application/json")

            # 2. Upload compiled dossier if present
            if dossier_bytes:
                pdf_key = f"{prefix}/{dossier_filename or 'dossier.pdf'}"
                content_type = "application/pdf" if pdf_key.endswith(".pdf") else "text/html"
                await self.upload_file(pdf_key, dossier_bytes, content_type)

            return True
        except Exception as e:
            logger.warning("Cloud storage export failed: %s", e)
            return False

    async def upload_file(self, path_key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        """Uploads a file to the configured storage backend and returns its URI or URL."""
        if self.backend == "gcs":
            return await self._upload_gcs(path_key, content, content_type)
        elif self.backend == "s3":
            return await self._upload_s3(path_key, content, content_type)
        else:
            return await self._upload_local(path_key, content)

    async def _upload_gcs(self, key: str, content: bytes, content_type: str) -> str:
        """Uploads object to Google Cloud Storage via JSON API or XML API."""
        # Standard GCS REST upload endpoint
        upload_url = f"https://storage.googleapis.com/upload/storage/v1/b/{self.bucket_name}/o?uploadType=media&name={key}"
        headers = {"Content-Type": content_type}

        # If OAuth / Service account Bearer token is provided via access_key
        if self.access_key:
            headers["Authorization"] = f"Bearer {self.access_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(upload_url, headers=headers, content=content)
            if res.status_code in (200, 201):
                logger.info("Successfully uploaded object to GCS bucket gs://%s/%s", self.bucket_name, key)
                return f"https://storage.googleapis.com/{self.bucket_name}/{key}"
            
            # Fallback to standard HTTP PUT endpoint
            direct_url = f"https://storage.googleapis.com/{self.bucket_name}/{key}"
            put_res = await client.put(direct_url, headers=headers, content=content)
            if put_res.status_code in (200, 201):
                return direct_url

        return f"gs://{self.bucket_name}/{key}"

    async def _upload_s3(self, key: str, content: bytes, content_type: str) -> str:
        """Uploads object to S3-compatible cloud storage with SigV4 signing."""
        if self.access_key and self.secret_key:
            target_url, headers = sign_s3_request(
                method="PUT",
                endpoint_url=self.endpoint_url,
                bucket=self.bucket_name,
                key=key,
                body=content,
                content_type=content_type,
                access_key=self.access_key,
                secret_key=self.secret_key,
                region=self.region,
            )
        else:
            base_endpoint = self.endpoint_url or f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com"
            target_url = f"{base_endpoint.rstrip('/')}/{key}"
            headers = {"Content-Type": content_type}

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.put(target_url, headers=headers, content=content)
            if res.status_code in (200, 201):
                return target_url

        return f"s3://{self.bucket_name}/{key}"

    def _write_local_file(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    async def _upload_local(self, key: str, content: bytes) -> str:
        """Saves file to local exports directory without blocking the async event loop."""
        import asyncio
        export_path = Path("exports") / key
        await asyncio.to_thread(self._write_local_file, export_path, content)
        logger.info("Saved export locally to %s", export_path)
        return str(export_path)

    async def test_connection(self) -> tuple[bool, str]:
        """Tests live reachability of the configured cloud storage bucket."""
        if self.backend == "local":
            Path("exports").mkdir(parents=True, exist_ok=True)
            return True, "Local export filesystem storage is available."

        if not self.bucket_name:
            return False, "Storage bucket name is required."

        if self.backend == "gcs":
            target_url = f"https://storage.googleapis.com/{self.bucket_name}"
            try:
                headers = {"User-Agent": "Orbit-GCS-Probe/1.0"}
                if self.access_key:
                    headers["Authorization"] = f"Bearer {self.access_key}"
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.head(target_url, headers=headers)
                    if res.status_code in (200, 204, 301, 302, 307, 403):
                        return True, f"Google Cloud Storage bucket 'gs://{self.bucket_name}' reachable."
                    if res.status_code == 404:
                        return False, f"GCS bucket 'gs://{self.bucket_name}' not found (HTTP 404)."
                    return False, f"GCS endpoint returned HTTP {res.status_code}."
            except Exception as e:
                logger.error("GCS connection probe failed: %s", e)
                return False, f"Could not reach Google Cloud Storage bucket 'gs://{self.bucket_name}'."

        if self.backend == "s3":
            target_host = self.endpoint_url or f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com"
            try:
                headers = {"User-Agent": "Orbit-S3-Probe/1.0"}
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.head(target_host, headers=headers)
                    if res.status_code in (200, 204, 301, 302, 307, 403):
                        return True, f"S3 bucket '{self.bucket_name}' ({self.region}) connectivity verified."
                    if res.status_code == 404:
                        return False, f"S3 bucket '{self.bucket_name}' not found (HTTP 404)."
                    return False, f"S3 endpoint returned HTTP {res.status_code}."
            except Exception as e:
                logger.error("S3 connection probe failed: %s", e)
                return False, f"Could not connect to S3 bucket '{self.bucket_name}'."

        return True, f"Storage backend '{self.backend}' configured."
