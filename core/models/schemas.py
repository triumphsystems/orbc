from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.models.execution_plan import ExecutionPlan


class GoalRequest(BaseModel):
    """Payload to create and interpret an autonomous web data automation."""
    goal: str = Field(..., min_length=5, description="Natural language objective for Orbit")


class AutomationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    raw_goal: str
    plan: ExecutionPlan
    active: bool = True
    created_at: str
    next_run_at: str | None = None


class ResultOut(BaseModel):
    id: str
    url: str | None = None
    data: dict[str, Any] = Field(default_factory=dict, description="Extracted dynamic fields")
    valid: bool
    validation_errors: list[str] | None = None
    created_at: str


class RunOut(BaseModel):
    id: str
    automation_id: str
    status: str
    started_at: str
    finished_at: str | None = None
    sources_found: list[str] | None = None
    pages_retrieved: list[str] | None = None
    extracted_count: int | None = 0
    validated_count: int | None = 0
    condition_matched: bool | None = None
    condition_message: str | None = None
    reasoning_log: list[dict[str, Any]] | None = None
    error: str | None = None
    results: list[ResultOut] = []


class AutomationListOut(BaseModel):
    items: list[AutomationOut]
    total: int
