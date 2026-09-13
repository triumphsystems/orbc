import asyncio
import hmac
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.agent.orchestrator import AgentOrchestrator
from core.api.dependencies import get_db
from core.config.settings import get_settings
from core.db.orm import Automation
from core.db.session import SessionLocal

logger = logging.getLogger("core.api.v1.scheduler")

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

orchestrator = AgentOrchestrator()


def verify_scheduler_auth(
    request: Request,
    x_scheduler_secret: str | None = Header(None, alias="X-Scheduler-Secret"),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Provider-agnostic authentication verifying Cloud Schedulers (GCP, AWS, Render, GitHub, etc.)."""
    settings = get_settings()
    configured_secret = (settings.scheduler_secret or "").strip()

    # If secret is configured, require exact timing-safe match
    if configured_secret:
        if x_scheduler_secret and hmac.compare_digest(x_scheduler_secret.strip(), configured_secret):
            return True

        if authorization:
            token = authorization.replace("Bearer ", "").replace("bearer ", "").strip()
            if hmac.compare_digest(token, configured_secret):
                return True

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: invalid or missing scheduler secret header.",
        )

    # In production environments, unauthenticated access is strictly forbidden
    if settings.app_env.lower() in ("production", "prod", "staging"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: SCHEDULER_SECRET must be configured in production to trigger scheduled automations.",
        )

    # In local development / testing, only allow local loopback / test requests
    client_host = request.client.host if request.client else "127.0.0.1"
    if client_host not in ("127.0.0.1", "localhost", "testclient", "::1"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: SCHEDULER_SECRET is required for non-local access.",
        )

    return True


@router.post("/trigger-due", summary="Trigger all due automations (Cloud Scheduler Hook)")
@router.post("/tick", summary="Alias for /trigger-due")
async def trigger_due_automations(
    db: Annotated[Session, Depends(get_db)],
    _: bool = Depends(verify_scheduler_auth),
    wait: bool = False,
):
    """
    Provider-agnostic cloud-native scheduler webhook.
    Works seamlessly with:
    - Google Cloud Scheduler (set ?wait=true for Cloud Run synchronous execution)
    - AWS EventBridge / Lambda
    - Render Cron Jobs
    - Fly.io / Railway / Heroku
    - GitHub Actions / Custom Crons
    """
    now_utc = datetime.now(timezone.utc)
    due_automations = (
        db.query(Automation)
        .filter(
            Automation.active.is_(True),
            Automation.next_run_at.isnot(None),
            Automation.next_run_at <= now_utc,
        )
        .all()
    )

    async def _execute_due_task(auto_id: str) -> dict[str, str]:
        with SessionLocal() as bg_db:
            bg_auto = bg_db.query(Automation).filter(Automation.id == auto_id).first()
            if bg_auto:
                try:
                    run = await orchestrator.execute_run(bg_db, bg_auto)
                    status_val = run.status.value if hasattr(run.status, "value") else str(run.status)
                    return {"automation_id": auto_id, "run_id": run.id, "status": status_val}
                except Exception as err:
                    logger.exception("Scheduled execution error for automation %s: %s", auto_id, err)
                    return {"automation_id": auto_id, "error": str(err)}
        return {"automation_id": auto_id, "error": "Automation not found"}

    tasks = []
    triggered_ids = []
    for auto in due_automations:
        try:
            # Atomic update: temporarily clear next_run_at to prevent double triggering on overlapping ticks
            auto.next_run_at = None
            db.commit()

            task_coro = _execute_due_task(auto.id)
            if wait:
                tasks.append(task_coro)
            else:
                asyncio.create_task(task_coro)

            triggered_ids.append(auto.id)
            logger.info("Cloud scheduler triggered execution for automation %s (wait=%s)", auto.id, wait)
        except Exception as e:
            logger.error("Failed to trigger scheduled execution for automation %s: %s", auto.id, e)

    execution_results = None
    if wait and tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_results = [
            r if isinstance(r, dict) else {"error": str(r)} for r in results
        ]

    response = {
        "status": "success",
        "due_count": len(due_automations),
        "triggered_automation_ids": triggered_ids,
        "wait": wait,
        "server_time_utc": now_utc.isoformat(),
    }
    if execution_results is not None:
        response["executions"] = execution_results

    return response



@router.get("/status", summary="Inspect upcoming scheduled automations")
def get_scheduler_status(
    db: Annotated[Session, Depends(get_db)],
    _: bool = Depends(verify_scheduler_auth),
):
    """Lists all active automations with their next scheduled execution time."""
    now_utc = datetime.now(timezone.utc)
    active_schedules = (
        db.query(Automation)
        .filter(Automation.active.is_(True), Automation.next_run_at.isnot(None))
        .order_by(Automation.next_run_at.asc())
        .all()
    )

    items = []
    for auto in active_schedules:
        plan = auto.plan or {}
        items.append({
            "automation_id": auto.id,
            "objective": plan.get("objective") or auto.raw_goal,
            "frequency": plan.get("frequency"),
            "schedule_time": plan.get("schedule_time"),
            "timezone": plan.get("timezone", "UTC"),
            "next_run_at": auto.next_run_at.isoformat() if auto.next_run_at else None,
            "is_due": auto.next_run_at <= now_utc if auto.next_run_at else False,
        })

    return {
        "server_time_utc": now_utc.isoformat(),
        "active_schedule_count": len(items),
        "schedules": items,
    }
