from typing import Any
from orbit.client import OrbitBackendClient


async def run_automation_tool(automation_id: str, client: OrbitBackendClient) -> dict[str, Any]:
    """
    Triggers an on-demand autonomous run for a registered automation.
    Executes the full pipeline via SSE streaming: discovery -> retrieval -> extraction -> validation -> condition evaluation -> verification.

    Args:
        automation_id: The UUID of the automation to execute.
    """
    try:
        initial_run = await client.run_automation(automation_id)
        run_id = initial_run.get("id")
        if not run_id:
            return {"success": False, "error": "Failed to initialize run"}

        # Stream live telemetry until completion
        run = await client.stream_run_and_wait(str(run_id))
        valid_results = [r for r in run.get("results", []) if r.get("valid")]

        return {
            "success": True,
            "run_id": run.get("id"),
            "automation_id": run.get("automation_id"),
            "status": run.get("status"),
            "sources_found_count": len(run.get("sources_found") or []),
            "pages_retrieved_count": len(run.get("pages_retrieved") or []),
            "extracted_count": run.get("extracted_count", 0),
            "validated_count": run.get("validated_count", 0),
            "condition_matched": run.get("condition_matched"),
            "condition_message": run.get("condition_message"),
            "valid_records": [
                {"url": r.get("url"), "data": r.get("data")} for r in valid_results
            ],
            "error": run.get("error"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def execute_goal_tool(goal: str, client: OrbitBackendClient) -> dict[str, Any]:
    """
    One-shot execution: Interprets a natural language goal, creates an automation,
    immediately executes the full agent loop with live streaming telemetry, and returns verified records.

    Args:
        goal: Natural language web data objective.
    """
    try:
        # Step 1: Create
        auto = await client.create_automation(goal)
        auto_id = auto.get("id")
        if not auto_id:
            return {"success": False, "error": "Failed to create automation"}

        # Step 2: Trigger & Stream
        initial_run = await client.run_automation(str(auto_id))
        run_id = initial_run.get("id")
        if not run_id:
            return {"success": False, "error": "Failed to initialize run"}

        run = await client.stream_run_and_wait(str(run_id))
        valid_results = [r for r in run.get("results", []) if r.get("valid")]

        return {
            "success": True,
            "automation_id": auto_id,
            "run_id": run.get("id"),
            "objective": auto.get("plan", {}).get("objective"),
            "domain": auto.get("plan", {}).get("domain"),
            "status": run.get("status"),
            "condition_matched": run.get("condition_matched"),
            "condition_message": run.get("condition_message"),
            "extracted_records_count": len(valid_results),
            "records": [
                {"url": r.get("url"), "data": r.get("data")} for r in valid_results
            ],
            "all_results": run.get("results", []),
            "error": run.get("error"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
