import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.session import Base
from core.models.enums import RunStatus


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Automation(Base):
    """Stored goal and dynamic execution plan."""

    __tablename__ = "automations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    raw_goal: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # stores serialized ExecutionPlan
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    runs: Mapped[list["Run"]] = relationship("Run", back_populates="automation", cascade="all, delete-orphan")


class Run(Base):
    """A single execution of an autonomous web-data automation."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    automation_id: Mapped[str] = mapped_column(String, ForeignKey("automations.id"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.pending, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Verification and provenance audit trail
    sources_found: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    pages_retrieved: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    extracted_count: Mapped[int] = mapped_column(Integer, default=0)
    validated_count: Mapped[int] = mapped_column(Integer, default=0)
    condition_matched: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    condition_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning_log: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    automation: Mapped["Automation"] = relationship("Automation", back_populates="runs")
    results: Mapped[list["Result"]] = relationship("Result", back_populates="run", cascade="all, delete-orphan")


class Result(Base):
    """A single extracted and validated record with dynamic domain-agnostic JSON payload."""

    __tablename__ = "results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False)

    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    valid: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_errors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped["Run"] = relationship("Run", back_populates="results")


class WorkflowPipeline(Base):
    """Stored autonomous workflow pipeline DAG with nodes and edges."""

    __tablename__ = "workflow_pipelines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, default="Active Pipeline")
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class AdapterConfig(Base):
    """Stored adapter credentials and configuration parameters."""

    __tablename__ = "adapter_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Template(Base):
    """Stored visual document templates and layout schemas."""

    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String, default="pdf")  # pdf | html | docx
    schema_definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


