from core.db.orm import Automation, Run
from core.models.execution_plan import ExecutionPlan
from core.models.schemas import AutomationOut, ResultOut, RunOut
from core.utils.sanitizer import sanitize_error_message


def automation_to_out(a: Automation) -> AutomationOut:
    try:
        plan = ExecutionPlan.model_validate(a.plan) if isinstance(a.plan, dict) else a.plan
    except Exception:
        plan = ExecutionPlan(objective=a.raw_goal or "Automation Plan", search_query=a.raw_goal or "")

    return AutomationOut(
        id=a.id,
        raw_goal=a.raw_goal,
        plan=plan,
        active=a.active,
        created_at=a.created_at.isoformat() if hasattr(a.created_at, "isoformat") else str(a.created_at),
        next_run_at=a.next_run_at.isoformat() if a.next_run_at and hasattr(a.next_run_at, "isoformat") else (str(a.next_run_at) if a.next_run_at else None),
    )


def result_to_out(res) -> ResultOut:
    return ResultOut(
        id=getattr(res, "id", ""),
        url=getattr(res, "url", None),
        data=getattr(res, "data", None) or {},
        valid=getattr(res, "valid", True),
        validation_errors=getattr(res, "validation_errors", None),
        created_at=res.created_at.isoformat() if getattr(res, "created_at", None) else "",
    )


def run_to_out(r: Run) -> RunOut:
    return RunOut(
        id=r.id,
        automation_id=r.automation_id,
        status=r.status.value if hasattr(r.status, "value") else str(r.status),
        started_at=r.started_at.isoformat(),
        finished_at=r.finished_at.isoformat() if r.finished_at else None,
        sources_found=r.sources_found,
        pages_retrieved=r.pages_retrieved,
        extracted_count=r.extracted_count,
        validated_count=r.validated_count,
        condition_matched=r.condition_matched,
        condition_message=r.condition_message,
        reasoning_log=r.reasoning_log,
        error=sanitize_error_message(r.error),
        results=[result_to_out(res) for res in r.results],
    )
