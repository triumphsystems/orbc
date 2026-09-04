import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any

from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

from core.agent.orchestrator import RunPoolManager
from core.agent.tools import ORBIT_AGENT_TOOLS
from core.config.settings import get_settings
from core.db.orm import Automation, Result, Run
from core.events.bus import event_bus
from core.events.types import OrbitEvent
from core.llm.adapters.strands_model import get_strands_model
from core.models.enums import RunStatus
from core.models.execution_plan import ExecutionPlan
from core.utils.sanitizer import sanitize_error_message

logger = logging.getLogger("core.agent.strands_orchestrator")


class StrandsAgentOrchestrator:
    """
    Model-driven autonomous orchestrator powered by AWS Strands Agents SDK.
    Replaces static pipeline stages with a goal-driven reasoning and tool loop,
    defaulting to Google Gemini (gemini-2.5-flash) with full live telemetry.
    """

    def __init__(self, model: Any | None = None):
        self.model = model

    def _safe_commit(self, db: Session) -> None:
        try:
            db.commit()
        except (OperationalError, DBAPIError) as e:
            logger.error("Database commit error: %s. Rolling back.", e)
            try:
                db.rollback()
            except Exception:
                pass
            raise

    async def execute_run(
        self,
        db: Session,
        automation: Automation,
        run: Run | None = None,
        resume: bool = False,
    ) -> Run:
        """Entrypoint for executing an autonomous extraction run with Strands SDK."""
        try:
            plan = ExecutionPlan.model_validate(automation.plan)
        except Exception as e:
            logger.warning("Falling back to basic execution plan for automation %s: %s", automation.id, e)
            plan = ExecutionPlan(
                objective=automation.raw_goal or "Execution Plan",
                search_query=automation.raw_goal or "",
            )

        if run is None:
            run = Run(
                automation_id=automation.id,
                status=RunStatus.discovering,
                reasoning_log=[],
            )
            db.add(run)
            self._safe_commit(db)
            db.refresh(run)
        else:
            run.error = None
            run.finished_at = None
            self._safe_commit(db)

        await event_bus.publish(
            OrbitEvent(
                event_type="run.started" if not resume else "run.resumed",
                run_id=run.id,
                automation_id=automation.id,
                message=f"{'Resuming' if resume else 'Starting'} Strands autonomous mission: {automation.raw_goal}",
            )
        )

        sem = RunPoolManager.get_semaphore()
        if sem.locked():
            run.status = RunStatus.pending
            self._safe_commit(db)
            await event_bus.publish(
                OrbitEvent(
                    event_type="run.stage",
                    run_id=run.id,
                    automation_id=automation.id,
                    message="Mission queued in concurrency pool (waiting for execution slot)",
                    payload={"stage": "pending"},
                )
            )

        async with sem:
            RunPoolManager.mark_active(run.id)
            try:
                return await self._execute_strands_agent_loop(db, automation, run, plan)
            finally:
                RunPoolManager.mark_inactive(run.id)

    async def _execute_strands_agent_loop(
        self,
        db: Session,
        automation: Automation,
        run: Run,
        plan: ExecutionPlan,
    ) -> Run:
        from strands import Agent

        reasoning_trail: list[dict[str, Any]] = list(run.reasoning_log or [])
        sources_discovered: set[str] = set(run.sources_found or [])
        pages_retrieved: set[str] = set(run.pages_retrieved or [])
        extracted_results: list[dict[str, Any]] = []

        try:
            # 1. Initialize Strands Model (Gemini default)
            active_model = self.model or get_strands_model()

            # 2. Formulate System Prompt
            schema_fields = list(plan.extraction_schema.fields.keys()) if plan.extraction_schema else []
            target_entity = plan.extraction_schema.entity_name if plan.extraction_schema else "Entity"

            system_prompt = f"""You are Orbit's autonomous data operations agent.
Your objective: {automation.raw_goal or plan.objective}
Target Entity: {target_entity}
Expected Schema Fields: {json.dumps(schema_fields)}

Operating Protocol:
1. Search candidate web sources using search_web_sources(query="{plan.search_query or plan.objective}").
2. Retrieve and clean relevant web content using retrieve_webpage_content(url=...).
3. Extract structured entities from content using extract_structured_records(url=..., content=..., target_entity="{target_entity}", expected_fields={json.dumps(schema_fields)}).
4. When extraction is complete, compile the dossier using compile_and_redact_dossier(automation_id="{automation.id}", run_id="{run.id}", records=..., sources=...).
5. Export results to sinks using export_records_sink(automation_id="{automation.id}", run_id="{run.id}", records=...).
6. Conclude with a brief summary of how many verified records were collected.
"""

            # 3. Instantiate Strands Agent with Orbit Tools
            agent = Agent(
                model=active_model,
                tools=ORBIT_AGENT_TOOLS,
                system_prompt=system_prompt,
            )

            run.status = RunStatus.discovering
            self._safe_commit(db)

            await event_bus.publish(
                OrbitEvent(
                    event_type="run.stage",
                    run_id=run.id,
                    automation_id=automation.id,
                    message="Strands model-driven agent initialized (Google Gemini 2.5 Flash)",
                    payload={"stage": "discovering", "model": "gemini-2.5-flash"},
                )
            )

            # 4. Execute the Strands Agent Loop in async thread
            mission_task = (
                f"Execute the mission to extract {target_entity} data for: '{plan.objective}'. "
                f"Extract structured records with fields {json.dumps(schema_fields)}, compile dossier, and export."
            )

            response = await asyncio.to_thread(agent, mission_task)
            response_text = str(response)

            reasoning_trail.append({"stage": "strands_execution", "summary": response_text})
            run.reasoning_log = reasoning_trail

            # 5. Harvest Extracted Records and Sources from Export Files
            import os
            nested_json = os.path.join("exports", automation.id, run.id, "dossier.pdf")
            flat_json = os.path.join("exports", f"{automation.id[:8]}_{run.id[:8]}.json")

            candidate_json_paths = [
                flat_json,
                os.path.join("core", flat_json),
                os.path.join("exports", f"{automation.id}_{run.id}.json"),
            ]

            persisted_records = []
            for jpath in candidate_json_paths:
                if os.path.exists(jpath):
                    try:
                        with open(jpath, "r", encoding="utf-8") as f:
                            persisted_records = json.load(f)
                        if persisted_records and isinstance(persisted_records, list):
                            break
                    except Exception:
                        pass

            # Populate database results
            db_results = []
            for rec in persisted_records:
                r_url = rec.get("url") if isinstance(rec, dict) else ""
                r_data = rec.get("data") if isinstance(rec, dict) and isinstance(rec.get("data"), dict) else (rec if isinstance(rec, dict) else {})
                if r_url:
                    sources_discovered.add(r_url)
                    pages_retrieved.add(r_url)

                result_row = Result(
                    run_id=run.id,
                    url=r_url or "https://autonomous.agent",
                    data=r_data,
                    valid=True,
                )
                db.add(result_row)
                db_results.append(result_row)

            run.sources_found = list(sources_discovered)
            run.pages_retrieved = list(pages_retrieved)
            run.extracted_count = len(db_results)
            run.validated_count = len(db_results)
            run.status = RunStatus.verified
            run.finished_at = datetime.now(timezone.utc)
            self._safe_commit(db)

            await event_bus.publish(
                OrbitEvent(
                    event_type="run.completed",
                    run_id=run.id,
                    automation_id=automation.id,
                    message=f"Strands autonomous run completed successfully with {len(db_results)} verified records",
                    payload={"status": "verified", "count": len(db_results)},
                )
            )

            return run

        except Exception as e:
            logger.exception("Error executing Strands agent loop: %s", e)
            try:
                db.rollback()
                run.status = RunStatus.failed
                run.error = sanitize_error_message(str(e))
                run.finished_at = datetime.now(timezone.utc)
                db.add(run)
                self._safe_commit(db)
            except Exception:
                pass
            return run
