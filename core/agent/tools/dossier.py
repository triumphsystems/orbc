import logging
from typing import Any
from strands import tool

logger = logging.getLogger("core.agent.tools.dossier")


@tool
async def compile_and_redact_dossier(
    automation_id: str,
    run_id: str,
    records: list[dict[str, Any]],
    plan_summary: str = "Orbit Autonomous Briefing",
    style: str = "html",
    template_id: str = "",
    sources: list[str] = [],
) -> dict[str, Any]:
    """
    Compiles verified records and sources into a standardized executive dossier (PDF/HTML)
    and applies automated PII compliance redaction (masking emails, cards, phone numbers).

    Args:
        automation_id: ID of the parent automation mission.
        run_id: ID of the current run.
        records: List of verified record dictionaries.
        plan_summary: High-level mission objective or summary.
        style: Dossier rendering style ('html' or 'template').
        template_id: Optional template GUID if using custom visual template.
        sources: List of verified candidate data source URLs.
    """
    from core.adapters.documents.factory import DocumentAdapterFactory
    from core.adapters.storage.local_export import LocalFileExportSink

    logger.info("Strands tool compile_and_redact_dossier: records=%d sources=%d", len(records), len(sources))
    doc_gen = DocumentAdapterFactory.get_generator(style=style)
    raw_dossier = await doc_gen.generate_dossier(
        automation_id=automation_id,
        run_id=run_id,
        records=records,
        plan_summary=plan_summary,
        template_id=template_id or None,
        sources=sources,
    )

    doc_redactor = DocumentAdapterFactory.get_redactor()
    dossier_bytes = await doc_redactor.redact_pii(raw_dossier)

    export_sink = LocalFileExportSink()
    await export_sink.export_results(
        automation_id, run_id, records, dossier_bytes=dossier_bytes, dossier_filename="dossier.pdf"
    )

    return {
        "status": "success",
        "dossier_size_bytes": len(dossier_bytes),
        "dossier_path": f"exports/{automation_id}/{run_id}/dossier.pdf",
    }
