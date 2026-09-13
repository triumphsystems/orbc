import json
import logging
from typing import Any
import httpx

from core.config.settings import get_settings

logger = logging.getLogger("core.adapters.documents.html_generator")


class HtmlDossierGenerator:
    """HTML/CSS rendering client for high-fidelity dossier generation."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.document_dossier_api_key
        self.base_url = (base_url or settings.document_dossier_base_url).rstrip("/")

    def _build_html_template(
        self,
        automation_id: str,
        run_id: str,
        records: list[dict[str, Any]],
        plan_summary: str | None,
        sources: list[str] | None = None,
    ) -> str:
        extracted_sources = list(sources or [])
        for r in records:
            u = r.get("url")
            if u and u not in extracted_sources:
                extracted_sources.append(u)

        sources_html = "".join(
            f"<li style='margin-bottom:4px;'><a href='{s}' target='_blank' style='color:#06b6d4;text-decoration:none;'>{s}</a></li>"
            for s in extracted_sources
        ) if extracted_sources else "<li>No verified source URLs logged.</li>"

        rows = "".join(
            f"<tr><td>{i+1}</td><td><a href='{r.get('url', '')}' target='_blank' style='color:#06b6d4;'>{r.get('url', 'N/A')}</a></td><td><code>{json.dumps(r.get('data', {}))}</code></td></tr>"
            for i, r in enumerate(records)
        )
        return f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>Orbit Dossier {run_id[:8]}</title>
<style>
body {{ font-family: monospace; padding: 24px; color: #1e293b; background: #f8fafc; }}
h1 {{ color: #0f172a; border-bottom: 2px solid #06b6d4; padding-bottom: 8px; }}
.sources-card {{ background: #e2e8f050; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; margin: 16px 0; font-size: 11px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 11px; }}
th, td {{ border: 1px solid #cbd5e1; padding: 6px 10px; text-align: left; }}
th {{ background: #e2e8f0; }}
</style></head>
<body>
<h1>Orbit Mission Intelligence Dossier</h1>
<p><strong>Mission:</strong> {automation_id} | <strong>Run:</strong> {run_id}</p>
<p><strong>Objective:</strong> {plan_summary or 'Autonomous Data Extraction'}</p>
<p><strong>Validated Records:</strong> {len(records)}</p>
<div class="sources-card">
  <strong>Verified Data Sources ({len(extracted_sources)}):</strong>
  <ul style="margin: 6px 0 0 0; padding-left: 20px; word-break: break-all;">{sources_html}</ul>
</div>
<table><thead><tr><th>#</th><th>Source URL</th><th>Extracted Payload</th></tr></thead>
<tbody>{rows}</tbody></table>
</body></html>"""

    async def generate_dossier(
        self,
        automation_id: str,
        run_id: str,
        records: list[dict[str, Any]],
        plan_summary: str | None = None,
        template_id: str | None = None,
        sources: list[str] | None = None,
    ) -> bytes:
        html = self._build_html_template(automation_id, run_id, records, plan_summary, sources=sources)
        if not self.api_key:
            return html.encode("utf-8")

        # Support both standard endpoint and custom endpoint URLs
        base = self.base_url.rstrip("/")
        url = f"{base}/build" if not base.endswith("/build") else base
        headers = {"Authorization": f"Bearer {self.api_key}"}

        instructions = json.dumps({
            "parts": [
                {
                    "html": "document.html",
                    "layout": {
                        "size": "A4",
                        "margin": {"top": 10, "bottom": 10, "left": 10, "right": 10},
                    },
                }
            ]
        })

        files = {
            "document.html": ("document.html", html.encode("utf-8"), "text/html"),
            "instructions": (None, instructions, "text/plain"),
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, files=files)
                res.raise_for_status()
                return res.content
        except Exception as e:
            logger.warning(f"HTML-to-PDF generation failed: {e}. Falling back to HTML bytes.")
            return html.encode("utf-8")
