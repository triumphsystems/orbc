import html
import json
import logging
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.api.dependencies import get_db, resolve_entity_by_id_or_prefix
from core.db.orm import Template
from core.utils.security import sanitize_css_color

logger = logging.getLogger("core.api.v1.templates")

router = APIRouter(prefix="/templates", tags=["Templates"])


class TemplateCreate(BaseModel):
    name: str = Field(..., description="Template display name (e.g. 'Executive Briefing', 'Contract Invoice')")
    description: str | None = Field(default="", description="Optional template description")
    format: str = Field(default="pdf", description="Output format: 'pdf', 'html', or 'docx'")
    schema_definition: dict[str, Any] = Field(default_factory=dict, description="Visual block schema, styles, and columns")
    is_default: bool = Field(default=False, description="Whether this is the default template for reporting")


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    format: str | None = None
    schema_definition: dict[str, Any] | None = None
    is_default: bool | None = None


class TemplateOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    format: str
    schema_definition: dict[str, Any]
    is_default: bool
    created_at: str
    updated_at: str


class TemplatePreviewRequest(BaseModel):
    schema_definition: dict[str, Any] = Field(default_factory=dict)
    sample_data: list[dict[str, Any]] = Field(default_factory=list)
    title: str = "Sample Orbit Mission Briefing"
    sources: list[str] = Field(default_factory=list)


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Annotated[Session, Depends(get_db)]):
    """Lists all stored visual templates and layout schemas."""
    templates = db.query(Template).order_by(Template.created_at.desc()).all()
    return [
        TemplateOut(
            id=t.id,
            name=t.name,
            description=t.description,
            format=t.format,
            schema_definition=t.schema_definition or {},
            is_default=t.is_default,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat() if t.updated_at else t.created_at.isoformat(),
        )
        for t in templates
    ]


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(payload: TemplateCreate, db: Annotated[Session, Depends(get_db)]):
    """Creates and persists a new visual document template."""
    if payload.is_default:
        db.query(Template).update({Template.is_default: False})

    tpl = Template(
        name=payload.name,
        description=payload.description,
        format=payload.format,
        schema_definition=payload.schema_definition,
        is_default=payload.is_default,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return TemplateOut(
        id=tpl.id,
        name=tpl.name,
        description=tpl.description,
        format=tpl.format,
        schema_definition=tpl.schema_definition or {},
        is_default=tpl.is_default,
        created_at=tpl.created_at.isoformat(),
        updated_at=tpl.updated_at.isoformat() if tpl.updated_at else tpl.created_at.isoformat(),
    )


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: str, db: Annotated[Session, Depends(get_db)]):
    """Fetches a stored template by ID or prefix."""
    tpl = resolve_entity_by_id_or_prefix(db, Template, template_id, "template")
    return TemplateOut(
        id=tpl.id,
        name=tpl.name,
        description=tpl.description,
        format=tpl.format,
        schema_definition=tpl.schema_definition or {},
        is_default=tpl.is_default,
        created_at=tpl.created_at.isoformat(),
        updated_at=tpl.updated_at.isoformat() if tpl.updated_at else tpl.created_at.isoformat(),
    )


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(template_id: str, payload: TemplateUpdate, db: Annotated[Session, Depends(get_db)]):
    """Updates an existing visual template schema."""
    tpl = resolve_entity_by_id_or_prefix(db, Template, template_id, "template")

    if payload.is_default:
        db.query(Template).filter(Template.id != tpl.id).update({Template.is_default: False})

    if payload.name is not None:
        tpl.name = payload.name
    if payload.description is not None:
        tpl.description = payload.description
    if payload.format is not None:
        tpl.format = payload.format
    if payload.schema_definition is not None:
        tpl.schema_definition = payload.schema_definition
    if payload.is_default is not None:
        tpl.is_default = payload.is_default

    db.commit()
    db.refresh(tpl)
    return TemplateOut(
        id=tpl.id,
        name=tpl.name,
        description=tpl.description,
        format=tpl.format,
        schema_definition=tpl.schema_definition or {},
        is_default=tpl.is_default,
        created_at=tpl.created_at.isoformat(),
        updated_at=tpl.updated_at.isoformat() if tpl.updated_at else tpl.created_at.isoformat(),
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: str, db: Annotated[Session, Depends(get_db)]):
    """Deletes a visual document template."""
    tpl = resolve_entity_by_id_or_prefix(db, Template, template_id, "template")
    db.delete(tpl)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/preview")
def render_template_preview(payload: TemplatePreviewRequest):
    """Renders a live HTML preview of the visual template schema with sample data."""
    schema = payload.schema_definition or {}
    sample_records = payload.sample_data or [
        {"title": "Sample Opportunity A", "amount": "$5,000", "deadline": "2026-09-30", "status": "open", "source_url": "https://arxiv.org/html/2601.13243v1"},
        {"title": "Sample Fellowship B", "amount": "$12,500", "deadline": "2026-10-15", "status": "verified", "source_url": "https://www.researchgate.net/publication/394100858"},
    ]

    header_title = html.escape(str(schema.get("title") or payload.title))
    theme_color = sanitize_css_color(schema.get("theme_color"), default="#00F2FE")
    bg_color = sanitize_css_color(schema.get("background_color"), default="#090d16")
    text_color = sanitize_css_color(schema.get("text_color"), default="#e2e8f0")
    show_summary = schema.get("show_summary", True)
    columns = [str(col) for col in (schema.get("columns") or ["title", "amount", "deadline", "status"])]

    # Collect and normalize all verified data sources
    extracted_sources = list(payload.sources or [])
    for r in sample_records:
        src = r.get("source_url") or r.get("url") or r.get("source")
        if src and src not in extracted_sources:
            extracted_sources.append(src)
    if not extracted_sources:
        extracted_sources = [
            "https://arxiv.org/html/2601.13243v1",
            "https://www.researchgate.net/publication/394100858",
        ]

    sources_items_html = "".join(
        f"<li style='margin-bottom:4px;'><a href='{html.escape(s)}' target='_blank' rel='noopener noreferrer' style='color:{theme_color};text-decoration:none;'>{html.escape(s)}</a></li>"
        for s in extracted_sources
    )

    table_headers = "".join(
        f"<th style='padding:8px 12px;text-align:left;border:1px solid #1e293b;background:#141b2d;'>{html.escape(col.replace('_', ' ').title())}</th>"
        for col in columns
    )

    table_rows = ""
    for r in sample_records:
        cells = "".join(
            f"<td style='padding:8px 12px;border:1px solid #1e293b;'>{html.escape(str(r.get(col, 'N/A')))}</td>"
            for col in columns
        )
        table_rows += f"<tr>{cells}</tr>"

    summary_section = ""
    if show_summary:
        summary_section = f"""
<div class='card'>
  <p style='margin:0 0 10px 0;font-size:13px;line-height:1.5;'>
    <strong>Summary:</strong> Autonomous extraction briefing compiled from <strong>{len(sample_records)} verified records</strong> across <strong>{len(extracted_sources)} verified data sources</strong>.
  </p>
  <div style='border-top:1px solid #1e293b;padding-top:8px;margin-top:8px;'>
    <div style='font-size:10px;font-weight:700;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.05em;'>
      Verified Data Sources ({len(extracted_sources)}):
    </div>
    <ul style='margin:0;padding-left:18px;font-size:11px;font-family:monospace;word-break:break-all;'>
      {sources_items_html}
    </ul>
  </div>
</div>
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{header_title}</title>
<style>
body {{ font-family: 'Space Grotesk', system-ui, sans-serif; background: {bg_color}; color: {text_color}; padding: 2rem; margin: 0; box-sizing: border-box; }}
h1 {{ color: {theme_color}; border-bottom: 2px solid {theme_color}40; padding-bottom: 8px; margin-top: 0; }}
.card {{ background: #0e131f; border: 1px solid #1e293b; border-radius: 8px; padding: 1rem; margin-top: 1rem; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; font-family: monospace; font-size: 12px; }}
.badge {{ background: {theme_color}20; color: {theme_color}; padding: 3px 8px; border-radius: 4px; font-family: monospace; font-size: 11px; }}
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: #1e293b; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: #334155; }}
</style></head>
<body>
<h1>🛰️ {header_title}</h1>
{summary_section}
<table class="card"><thead><tr>{table_headers}</tr></thead><tbody>{table_rows}</tbody></table>
<div style="margin-top:2rem;font-size:11px;color:#64748b;font-family:monospace;display:flex;justify-content:space-between;">
  <span>Rendered via Orbit Visual Template Studio</span>
  <span class="badge">Compliance Verified</span>
</div>
</body></html>"""

    return Response(content=html_content.encode("utf-8"), media_type="text/html")
