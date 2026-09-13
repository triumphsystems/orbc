import json
import logging
from typing import Any
import httpx

from core.config.settings import get_settings

logger = logging.getLogger("core.adapters.documents.template_generator")


class TemplateDossierGenerator:
    """Enterprise template merging client for populating Word/PDF templates."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.document_template_api_key
        self.base_url = (base_url or settings.document_template_base_url).rstrip("/")

    async def generate_dossier(
        self,
        automation_id: str,
        run_id: str,
        records: list[dict[str, Any]],
        plan_summary: str | None = None,
        template_id: str | None = None,
        sources: list[str] | None = None,
    ) -> bytes:
        """Merges extracted records into a document template via Doctavian / Enterprise Engine."""
        extracted_sources = list(sources or [])
        for r in records:
            u = r.get("url")
            if u and u not in extracted_sources:
                extracted_sources.append(u)

        data_payload = {
            "automation_id": automation_id,
            "run_id": run_id,
            "summary": plan_summary or "Orbit Data Briefing",
            "record_count": len(records),
            "sources": extracted_sources,
            "records": [
                r.get("data") if isinstance(r, dict) and isinstance(r.get("data"), dict) else (r if isinstance(r, dict) else {})
                for r in records
            ],
        }

        if not self.api_key:
            return json.dumps(data_payload, indent=2).encode("utf-8")

        headers = {
            "X-Api-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                json_bytes = json.dumps(data_payload, indent=2).encode("utf-8")

                # Step 1: Upload JSON data payload to document engine
                data_upload_url = f"{self.base_url}/documents/data/upload" if not self.base_url.endswith("/upload") else self.base_url
                files = {"file": ("data.json", json_bytes, "application/json")}
                
                upload_res = await client.post(data_upload_url, headers=headers, files=files)
                
                data_urn = ""
                if upload_res.status_code in (200, 201):
                    upload_json = upload_res.json()
                    files_list = upload_json.get("result", {}).get("data", {}).get("files", [])
                    if files_list and isinstance(files_list, list):
                        data_urn = files_list[0].get("id", "")
                    elif "id" in upload_json.get("result", {}).get("data", {}):
                        data_urn = upload_json["result"]["data"]["id"]
                    elif "id" in upload_json:
                        data_urn = upload_json["id"]

                # Step 2: Request document compilation from template & uploaded data
                generate_url = f"{self.base_url}/documents/document/generate" if not self.base_url.endswith("/generate") else self.base_url
                generate_headers = {**headers, "Content-Type": "application/json"}
                
                template_name = f"{template_id or 'briefing'}.docx"
                effective_template_urn = template_id or "default-executive-template"

                generate_body: dict[str, Any] = {
                    "externalContext": {"id": f"orbit-{run_id[:8]}"},
                    "template": {
                        "name": template_name,
                        "urn": effective_template_urn,
                        "fileFormat": "docx",
                        "loadMethod": "Storage",
                        "options": {},
                    },
                    "data": {
                        "loadMethod": "Storage" if data_urn else "Inline",
                        "urn": data_urn if data_urn else "",
                    },
                    "document": {
                        "name": f"Orbit-Dossier-{run_id[:8]}",
                        "fileFormat": "pdf",
                        "deliveryMethod": "Storage",
                        "path": "root",
                        "locale": "en",
                        "timezone": "UTC",
                        "options": {},
                    },
                }
                if not data_urn:
                    generate_body["data"]["payload"] = data_payload

                gen_res = await client.post(generate_url, headers=generate_headers, json=generate_body)
                
                # Check for direct PDF response
                if gen_res.status_code in (200, 201) and gen_res.headers.get("content-type", "").startswith("application/pdf"):
                    return gen_res.content

                if gen_res.status_code in (200, 201):
                    gen_json = gen_res.json()
                    doc_obj = gen_json.get("result", {}).get("data", {}).get("document", {})
                    doc_id = doc_obj.get("id") or gen_json.get("result", {}).get("data", {}).get("id") or gen_json.get("id")
                    
                    if doc_id:
                        # Step 3: Download compiled document PDF bytes
                        download_url = f"{self.base_url}/documents/document/{doc_id}/download"
                        dl_res = await client.get(download_url, headers=headers)
                        dl_res.raise_for_status()
                        return dl_res.content

                gen_res.raise_for_status()
                return gen_res.content

        except Exception as e:
            logger.warning(f"Template merging failed: {e}. Falling back to structured JSON.")
            return json.dumps(data_payload, indent=2).encode("utf-8")
