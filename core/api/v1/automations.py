import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.agent.interpreter import GoalInterpreter
from core.agent.orchestrator import AgentOrchestrator
from core.api.dependencies import get_db, resolve_entity_by_id_or_prefix
from core.api.rate_limiter import rate_limit
from core.api.serializers import automation_to_out, run_to_out
from core.db.orm import Automation, Run
from core.db.session import SessionLocal
from core.events.sse import format_sse, sse_response
from core.models.enums import RunStatus
from core.models.schemas import AutomationListOut, AutomationOut, GoalRequest, RunOut

logger = logging.getLogger("core.api.v1.automations")

router = APIRouter(prefix="/automations", tags=["Automations"])

interpreter = GoalInterpreter()
orchestrator = AgentOrchestrator()


@router.get("/plan/stream", dependencies=[Depends(rate_limit("goal"))])
async def stream_goal_plan(goal: str):
    """
    Streams LLM goal interpretation, reasoning tokens, and execution plan synthesis via Server-Sent Events (SSE).
    """
    if not goal or not goal.strip():
        raise HTTPException(status_code=400, detail="A goal description must be provided.")

    target_goal = goal.strip()

    async def event_generator():
        try:
            final_plan_dict = None
            async for evt in interpreter.interpret_stream(target_goal):
                if evt["event"] == "plan":
                    final_plan_dict = evt["data"]
                yield format_sse(data=evt["data"], event=evt["event"])

            if final_plan_dict:
                with SessionLocal() as db:
                    automation = Automation(
                        raw_goal=target_goal,
                        plan=final_plan_dict,
                        active=True,
                    )
                    db.add(automation)
                    db.commit()
                    db.refresh(automation)
                    out = automation_to_out(automation)
                yield format_sse(data=out, event="complete")
        except Exception as e:
            logger.exception("Error during streaming goal interpretation: %s", e)
            yield format_sse(data={"detail": str(e)}, event="error")

    return sse_response(event_generator())


@router.post("", response_model=AutomationOut, dependencies=[Depends(rate_limit("goal"))])
async def create_automation(payload: GoalRequest, db: Annotated[Session, Depends(get_db)]):
    """Interprets a natural-language goal into a dynamic execution plan and creates an automation."""
    try:
        plan = await interpreter.interpret(payload.goal)
    except ValueError as e:
        logger.warning("Goal interpretation validation failed: %s", e)
        raise HTTPException(
            status_code=400,
            detail="The provided goal could not be processed into an execution plan. Please provide a more descriptive objective.",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during goal interpretation")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while synthesizing the execution plan. Please try again.",
        ) from e

    automation = Automation(
        raw_goal=payload.goal,
        plan=plan.model_dump(),
        active=True,
    )
    db.add(automation)
    db.commit()
    db.refresh(automation)

    return automation_to_out(automation)


@router.get("", response_model=AutomationListOut)
def list_automations(db: Annotated[Session, Depends(get_db)]):
    """Retrieves all registered automations."""
    records = db.query(Automation).order_by(Automation.created_at.desc()).all()
    items = [automation_to_out(a) for a in records]
    return AutomationListOut(items=items, total=len(items))


@router.get("/{automation_id}", response_model=AutomationOut)
def get_automation(automation_id: str, db: Annotated[Session, Depends(get_db)]):
    """Retrieves a single automation by its ID or unambiguous prefix."""
    automation = resolve_entity_by_id_or_prefix(db, Automation, automation_id, "automation")
    return automation_to_out(automation)


@router.post("/{automation_id}/run", response_model=RunOut, dependencies=[Depends(rate_limit("run"))])
async def run_automation(automation_id: str, db: Annotated[Session, Depends(get_db)]):
    """Triggers an on-demand autonomous run immediately in background and returns initial run metadata."""
    automation = resolve_entity_by_id_or_prefix(db, Automation, automation_id, "automation")

    # Layer 2: Prevent concurrent overlapping runs for the same automation
    active_run = (
        db.query(Run)
        .filter(
            Run.automation_id == automation.id,
            ~Run.status.in_([RunStatus.verified, RunStatus.failed]),
        )
        .first()
    )
    if active_run:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Automation '{automation.id[:8]}' already has an active run in progress "
                f"(run: {active_run.id[:8]}, status: '{active_run.status.value}'). "
                "Please wait for the current run to complete before starting a new one."
            ),
        )

    # 1. Create run record in discovering status
    run = Run(
        automation_id=automation.id,
        status=RunStatus.discovering,
        reasoning_log=[],
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # 2. Async background executor with isolated session
    async def _execute_pipeline(auto_id: str, r_id: str):
        with SessionLocal() as bg_db:
            bg_auto = bg_db.query(Automation).filter(Automation.id == auto_id).first()
            bg_run = bg_db.query(Run).filter(Run.id == r_id).first()
            if bg_auto and bg_run:
                try:
                    await orchestrator.execute_run(bg_db, bg_auto, run=bg_run)
                except Exception as err:
                    logger.exception("Background execution error for run %s: %s", r_id, err)

    asyncio.create_task(_execute_pipeline(automation.id, run.id))
    return run_to_out(run)


@router.delete("/{automation_id}")
def delete_automation(automation_id: str, db: Annotated[Session, Depends(get_db)]):
    """Deletes an automation and all its associated runs and results."""
    automation = resolve_entity_by_id_or_prefix(db, Automation, automation_id, "automation")

    db.delete(automation)
    db.commit()
    return {"message": "Automation deleted successfully"}
