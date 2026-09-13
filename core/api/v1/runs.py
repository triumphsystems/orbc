import asyncio
import html
import json
import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.agent.orchestrator import AgentOrchestrator, RunPoolManager
from core.api.dependencies import get_db, resolve_entity_by_id_or_prefix
from core.api.rate_limiter import rate_limit
from core.api.serializers import result_to_out, run_to_out
from core.db.orm import Automation, Result, Run
from core.db.session import SessionLocal
from core.events.bus import event_bus
from core.events.sse import format_sse, format_sse_ping, sse_response
from core.events.types import OrbitEvent
from core.models.enums import RunStatus
from core.models.schemas import RunOut

logger = logging.getLogger("core.api.v1.runs")

router = APIRouter(tags=["Runs"])
orchestrator = AgentOrchestrator()


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Annotated[Session, Depends(get_db)]):
    """Retrieves detailed execution audit trail and results for a specific run."""
    run = resolve_entity_by_id_or_prefix(db, Run, run_id, "run")
    return run_to_out(run)


@router.get("/runs/{run_id}/stream")
async def stream_run_telemetry(run_id: str, request: Request, db: Annotated[Session, Depends(get_db)]):
    """
    Streams live run telemetry, stage transitions, reasoning logs, and status updates via Server-Sent Events (SSE).
    """
    run = resolve_entity_by_id_or_prefix(db, Run, run_id, "run")
    canonical_run_id = run.id
    initial_payload = run_to_out(run)

    async def event_generator():
        # 1. Send initial snapshot immediately
        yield format_sse(data=initial_payload, event="snapshot")

        # If already completed or failed, close the stream cleanly
        if initial_payload.status in (RunStatus.verified, RunStatus.failed):
            yield format_sse(data=initial_payload, event="complete")
            return

        queue: asyncio.Queue[OrbitEvent | None] = asyncio.Queue()

        async def _on_event(evt: OrbitEvent):
            if evt.run_id == canonical_run_id:
                await queue.put(evt)

        event_bus.subscribe(_on_event)

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if evt is None:
                        break

                    with SessionLocal() as poll_db:
                        current_run = poll_db.query(Run).filter(Run.id == canonical_run_id).first()
                        if current_run:
                            out = run_to_out(current_run)
                            event_name = "complete" if out.status in (RunStatus.verified, RunStatus.failed) else "update"
                            yield format_sse(data=out, event=event_name)

                            if out.status in (RunStatus.verified, RunStatus.failed):
                                break
                except asyncio.TimeoutError:
                    with SessionLocal() as poll_db:
                        current_run = poll_db.query(Run).filter(Run.id == canonical_run_id).first()
                        if current_run:
                            out = run_to_out(current_run)
                            if out.status in (RunStatus.verified, RunStatus.failed):
                                yield format_sse(data=out, event="complete")
                                break
                    yield format_sse_ping()
        finally:
            event_bus.unsubscribe(_on_event)

    return sse_response(event_generator())


@router.get("/runs/{run_id}/results/stream")
async def stream_run_results(run_id: str, request: Request, db: Annotated[Session, Depends(get_db)]):
    """
    Streams extracted and validated data entities incrementally via Server-Sent Events (SSE).
    """
    run = resolve_entity_by_id_or_prefix(db, Run, run_id, "run")
    canonical_run_id = run.id

    async def event_generator():
        sent_ids = set()

        # 1. Stream existing records first
        with SessionLocal() as cur_db:
            existing_results = cur_db.query(Result).filter(Result.run_id == canonical_run_id).all()
            for res in existing_results:
                sent_ids.add(res.id)
                yield format_sse(data=result_to_out(res), event="record")

        # If already finished, terminate
        with SessionLocal() as cur_db:
            cur_run = cur_db.query(Run).filter(Run.id == canonical_run_id).first()
            if cur_run and cur_run.status in (RunStatus.verified, RunStatus.failed):
                yield format_sse(data={"total": len(sent_ids), "status": cur_run.status.value}, event="complete")
                return

        queue: asyncio.Queue[OrbitEvent | None] = asyncio.Queue()

        async def _on_event(evt: OrbitEvent):
            if evt.run_id == canonical_run_id:
                await queue.put(evt)

        event_bus.subscribe(_on_event)

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if evt is None:
                        break

                    with SessionLocal() as cur_db:
                        new_results = (
                            cur_db.query(Result)
                            .filter(Result.run_id == canonical_run_id, ~Result.id.in_(sent_ids) if sent_ids else True)
                            .all()
                        )
                        for res in new_results:
                            sent_ids.add(res.id)
                            yield format_sse(data=result_to_out(res), event="record")

                        cur_run = cur_db.query(Run).filter(Run.id == canonical_run_id).first()
                        if cur_run and cur_run.status in (RunStatus.verified, RunStatus.failed):
                            yield format_sse(data={"total": len(sent_ids), "status": cur_run.status.value}, event="complete")
                            break
                except asyncio.TimeoutError:
                    with SessionLocal() as cur_db:
                        new_results = (
                            cur_db.query(Result)
                            .filter(Result.run_id == canonical_run_id, ~Result.id.in_(sent_ids) if sent_ids else True)
                            .all()
                        )
                        for res in new_results:
                            sent_ids.add(res.id)
                            yield format_sse(data=result_to_out(res), event="record")

                        cur_run = cur_db.query(Run).filter(Run.id == canonical_run_id).first()
                        if cur_run and cur_run.status in (RunStatus.verified, RunStatus.failed):
                            yield format_sse(data={"total": len(sent_ids), "status": cur_run.status.value}, event="complete")
                            break
                    yield format_sse_ping()
        finally:
            event_bus.unsubscribe(_on_event)

    return sse_response(event_generator())


@router.get("/runs/{run_id}/dossier")
def get_run_dossier(run_id: str, request: Request, db: Annotated[Session, Depends(get_db)]):
    """Streams the generated and redacted PDF/HTML report dossier with RFC 7234 ETag caching."""
    run = resolve_entity_by_id_or_prefix(db, Run, run_id, "run")

    updated_ts = int(run.finished_at.timestamp() if run.finished_at else (run.started_at.timestamp() if run.started_at else 0))
    etag = f'W/"{run.id[:12]}-{updated_ts}"'

    headers = {
        "ETag": etag,
        "Cache-Control": "public, max-age=86400, stale-while-revalidate=3600" if run.status in (RunStatus.verified, RunStatus.failed) else "no-cache",
    }

    if request.headers.get("if-none-match") == etag or request.headers.get("If-None-Match") == etag:
        return Response(status_code=304, headers=headers)

    # 1. Resolve potential on-disk dossier paths across root and core export locations
    search_dirs = ["exports", os.path.join("core", "exports"), os.path.join("..", "exports")]
    candidate_paths = []
    for edir in search_dirs:
        if not os.path.exists(edir):
            continue
        candidate_paths.append(os.path.join(edir, run.automation_id, run.id, "dossier.pdf"))
        candidate_paths.append(os.path.join(edir, f"{run.automation_id[:8]}_{run.id[:8]}_dossier.pdf"))
        candidate_paths.append(os.path.join(edir, f"{run.automation_id}_{run.id}_dossier.pdf"))
        run_prefix = run.id[:8]
        try:
            for fname in os.listdir(edir):
                if run_prefix in fname and fname.endswith("_dossier.pdf"):
                    candidate_paths.append(os.path.join(edir, fname))
        except Exception:
            pass

    for p in candidate_paths:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            try:
                with open(p, "rb") as f:
                    head = f.read(16)
                if head.startswith(b"%PDF"):
                    return FileResponse(p, media_type="application/pdf", headers=headers)
                elif head.startswith(b"<!DOCTYPE") or head.startswith(b"<html"):
                    return FileResponse(p, media_type="text/html", headers=headers)
            except Exception as e:
                logger.warning("Failed inspecting dossier file candidate %s: %s", p, e)

    # 2. Dynamically compile complete interactive HTML dossier embedding sources and verified records
    goal = html.escape(run.automation.raw_goal if run.automation else "Autonomous Extraction Mission")
    sources = run.sources_found or []
    pages = run.pages_retrieved or []
    results = run.results or []

    sources_html = "".join(
        f"<li><a href='{html.escape(s)}' target='_blank' rel='noopener noreferrer'>{html.escape(s)}</a></li>"
        for s in sources
    ) or "<li style='color:#64748b;'>No candidate source URLs logged.</li>"

    pages_html = "".join(
        f"<li><a href='{html.escape(p)}' target='_blank' rel='noopener noreferrer'>{html.escape(p)}</a></li>"
        for p in pages
    ) or "<li style='color:#64748b;'>No retrieved page URLs logged.</li>"

    records_rows = ""
    for idx, r in enumerate(results):
        r_url = html.escape(r.url or "N/A")
        r_url_link = f"<a href='{r_url}' target='_blank' rel='noopener noreferrer'>{r_url}</a>" if r.url else "N/A"
        badge_cls = "badge-green" if r.valid else "badge-amber"
        badge_txt = "VERIFIED" if r.valid else "FLAGGED"
        payload_json = html.escape(json.dumps(r.data or {}, indent=2, default=str))

        records_rows += f"""
        <tr>
            <td style="text-align:center;font-weight:bold;color:#64748b;">{idx + 1}</td>
            <td style="max-width:260px;word-break:break-all;">{r_url_link}</td>
            <td style="text-align:center;"><span class="badge {badge_cls}">{badge_txt}</span></td>
            <td><pre class="code-block">{payload_json}</pre></td>
        </tr>
        """

    if not records_rows:
        records_rows = "<tr><td colspan='4' style='text-align:center;padding:24px;color:#64748b;'>No extraction records found for this run.</td></tr>"

    html_report = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Orbit Intelligence Dossier - Run {run.id[:8]}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #090d16;
    color: #e2e8f0;
    margin: 0;
    padding: 2rem;
    box-sizing: border-box;
  }}
  .container {{ max-width: 1000px; margin: 0 auto; }}
  .header {{
    border-bottom: 2px solid #00F2FE40;
    padding-bottom: 1.25rem;
    margin-bottom: 1.5rem;
  }}
  h1 {{ margin: 0 0 0.5rem 0; color: #00F2FE; font-size: 1.5rem; letter-spacing: -0.025em; }}
  .objective {{ color: #94a3b8; font-size: 0.95rem; margin: 0 0 1rem 0; }}
  .meta-pills {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
  .badge {{
    display: inline-flex;
    align-items: center;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-family: monospace;
    font-weight: 600;
    background: #141b2d;
    border: 1px solid #1e293b;
    color: #94a3b8;
  }}
  .badge-cyan {{ background: #00f2fe15; border-color: #00f2fe40; color: #00F2FE; }}
  .badge-green {{ background: #10b98115; border-color: #10b98140; color: #34d399; }}
  .badge-amber {{ background: #f59e0b15; border-color: #f59e0b40; color: #fbbf24; }}
  .card {{
    background: #0e131f;
    border: 1px solid #1e293b;
    border-radius: 0.75rem;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
  }}
  .card-title {{
    margin: 0 0 0.75rem 0;
    font-size: 0.95rem;
    color: #f1f5f9;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}
  ul.source-list {{ margin: 0; padding-left: 1.25rem; font-size: 0.82rem; font-family: monospace; }}
  ul.source-list li {{ margin-bottom: 0.35rem; word-break: break-all; }}
  ul.source-list a {{ color: #38bdf8; text-decoration: none; }}
  ul.source-list a:hover {{ text-decoration: underline; }}
  table.data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
    margin-top: 0.5rem;
  }}
  table.data-table th {{
    background: #141b2d;
    border: 1px solid #1e293b;
    padding: 0.6rem 0.75rem;
    text-align: left;
    color: #94a3b8;
    font-family: monospace;
  }}
  table.data-table td {{
    border: 1px solid #1e293b;
    padding: 0.6rem 0.75rem;
    vertical-align: top;
  }}
  table.data-table a {{ color: #38bdf8; text-decoration: none; }}
  table.data-table a:hover {{ text-decoration: underline; }}
  pre.code-block {{
    margin: 0;
    background: #07090e;
    border: 1px solid #1e293b;
    border-radius: 0.375rem;
    padding: 0.5rem;
    font-size: 0.75rem;
    color: #cbd5e1;
    overflow-x: auto;
    white-space: pre-wrap;
    max-height: 240px;
  }}
  .footer {{
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #1e293b;
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #64748b;
    font-family: monospace;
  }}
  .btn-print {{
    background: #00f2fe15;
    border: 1px solid #00f2fe40;
    color: #00F2FE;
    padding: 0.4rem 0.8rem;
    border-radius: 0.5rem;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s ease;
  }}
  .btn-print:hover {{
    background: #00f2fe25;
    border-color: #00f2fe80;
  }}
  @media print {{
    body {{
      background: #ffffff !important;
      color: #0f172a !important;
      padding: 0 !important;
    }}
    .no-print {{ display: none !important; }}
    .container {{ max-width: 100% !important; }}
    .header {{ border-bottom: 2px solid #0f172a !important; }}
    h1 {{ color: #0f172a !important; }}
    .objective {{ color: #475569 !important; }}
    .card {{
      background: #ffffff !important;
      border: 1px solid #cbd5e1 !important;
      box-shadow: none !important;
      page-break-inside: avoid;
    }}
    .card-title {{ color: #0f172a !important; }}
    ul.source-list a {{ color: #0284c7 !important; text-decoration: underline !important; }}
    table.data-table th {{
      background: #f1f5f9 !important;
      color: #0f172a !important;
      border: 1px solid #cbd5e1 !important;
    }}
    table.data-table td {{
      border: 1px solid #cbd5e1 !important;
      color: #1e293b !important;
    }}
    pre.code-block {{
      background: #f8fafc !important;
      color: #0f172a !important;
      border: 1px solid #cbd5e1 !important;
    }}
    .badge {{ border: 1px solid #cbd5e1 !important; }}
    .badge-cyan {{ color: #0369a1 !important; background: #e0f2fe !important; }}
    .badge-green {{ color: #15803d !important; background: #dcfce7 !important; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;">
      <div>
        <h1>🛰️ Orbit Mission Intelligence Dossier</h1>
        <p class="objective"><strong>Objective:</strong> {goal}</p>
      </div>
      <div class="no-print">
        <button onclick="window.print()" class="btn-print">🖨️ Save as PDF</button>
      </div>
    </div>
    <div class="meta-pills">
      <span class="badge">Run: {run.id[:8]}</span>
      <span class="badge badge-cyan">Status: {run.status.value.upper()}</span>
      <span class="badge badge-green">Compliance PII Redacted</span>
      <span class="badge">Records: {run.extracted_count}</span>
    </div>
  </div>

  <div class="card">
    <div class="card-title">🌐 Discovered Data Sources ({len(sources)})</div>
    <ul class="source-list">{sources_html}</ul>
  </div>

  <div class="card">
    <div class="card-title">📄 Retrieved Pages ({len(pages)})</div>
    <ul class="source-list">{pages_html}</ul>
  </div>

  <div class="card">
    <div class="card-title">📊 Extracted & Validated Records ({len(results)})</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 40px; text-align: center;">#</th>
          <th>Source URL</th>
          <th style="width: 90px; text-align: center;">Status</th>
          <th>Data Payload</th>
        </tr>
      </thead>
      <tbody>{records_rows}</tbody>
    </table>
  </div>

  <div class="footer">
    <span>Generated by Orbit Autonomous Data Operations</span>
    <span>{run.finished_at.isoformat() if run.finished_at else 'Active Execution'}</span>
  </div>
</div>
</body>
</html>"""
    return Response(content=html_report.encode("utf-8"), media_type="text/html", headers=headers)


@router.post("/runs/{run_id}/compile-dossier")
async def compile_run_dossier(
    run_id: str,
    db: Annotated[Session, Depends(get_db)],
    style: str = "html",
    template_id: str | None = None,
):
    """Compiles and exports a dossier PDF/HTML for an already completed run on-demand."""
    from core.adapters.documents.factory import DocumentAdapterFactory
    from core.adapters.storage.local_export import LocalFileExportSink

    run = resolve_entity_by_id_or_prefix(db, Run, run_id, "run")
    records = [
        {"url": r.url, "data": r.data, "valid": r.valid}
        for r in (run.results or [])
    ]
    sources = run.sources_found or run.pages_retrieved or []

    doc_gen = DocumentAdapterFactory.get_generator(style=style)
    raw_dossier = await doc_gen.generate_dossier(
        run.automation_id,
        run.id,
        records,
        plan_summary=run.automation.raw_goal if run.automation else None,
        template_id=template_id,
        sources=sources,
    )
    doc_redactor = DocumentAdapterFactory.get_redactor()
    dossier_bytes = await doc_redactor.redact_pii(raw_dossier)

    export_sink = LocalFileExportSink()
    await export_sink.export_results(
        run.automation_id, run.id, records, dossier_bytes=dossier_bytes, dossier_filename="dossier.pdf"
    )

    return {
        "status": "success",
        "run_id": run.id,
        "dossier_size_bytes": len(dossier_bytes),
        "download_url": f"/api/v1/runs/{run.id}/dossier",
    }


@router.post("/runs/{run_id}/retry", response_model=RunOut, dependencies=[Depends(rate_limit("run"))])
async def retry_run(run_id: str, db: Annotated[Session, Depends(get_db)]):
    """Resumes and retries execution of an existing run from its last checkpoint in background."""
    run = resolve_entity_by_id_or_prefix(db, Run, run_id, "run")

    if RunPoolManager.is_run_active(run.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run '{run.id[:8]}' is currently executing in background. Cannot trigger concurrent retry.",
        )

    automation = db.query(Automation).filter(Automation.id == run.automation_id).first()
    if not automation:
        raise HTTPException(status_code=404, detail="Parent automation not found")

    run.status = RunStatus.retrieving if run.sources_found else RunStatus.discovering
    run.error, run.finished_at = None, None
    db.commit()
    db.refresh(run)

    async def _execute_retry(auto_id: str, r_id: str):
        with SessionLocal() as bg_db:
            bg_auto = bg_db.query(Automation).filter(Automation.id == auto_id).first()
            bg_run = bg_db.query(Run).filter(Run.id == r_id).first()
            if bg_auto and bg_run:
                try:
                    await orchestrator.execute_run(bg_db, bg_auto, run=bg_run, resume=True)
                except Exception as err:
                    logger.exception("Background execution error in run %s: %s", r_id, err)

    asyncio.create_task(_execute_retry(automation.id, run.id))
    return run_to_out(run)


@router.get("/automations/{automation_id}/runs", response_model=list[RunOut])
def list_automation_runs(
    automation_id: str,
    db: Annotated[Session, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
):
    """Lists past execution history for a given automation with pagination support."""
    automation = resolve_entity_by_id_or_prefix(db, Automation, automation_id, "automation")
    runs = (
        db.query(Run)
        .filter(Run.automation_id == automation.id)
        .order_by(Run.started_at.desc())
        .offset(offset)
        .limit(min(max(1, limit), 100))
        .all()
    )
    return [run_to_out(r) for r in runs]
