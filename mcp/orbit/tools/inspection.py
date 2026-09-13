from typing import Any
from orbit.client import OrbitBackendClient


async def get_run_details_tool(run_id: str, client: OrbitBackendClient) -> dict[str, Any]:
    """
    Retrieves full execution audit trail, provenance (sources discovered, pages retrieved),
    reasoning logs, and validation errors for a specific run.

    Args:
        run_id: The UUID of the run to inspect.
    """
    try:
        run = await client.get_run(run_id)
        return {"success": True, "run": run}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def query_extracted_data_tool(
    run_id: str, valid_only: bool, client: OrbitBackendClient
) -> dict[str, Any]:
    """
    Queries and filters extracted records for a specific run.

    Args:
        run_id: The UUID of the run.
        valid_only: If True, filters out records that failed schema validation.
    """
    try:
        run = await client.get_run(run_id)
        results = run.get("results", [])
        if valid_only:
            results = [r for r in results if r.get("valid")]

        return {
            "success": True,
            "run_id": run_id,
            "status": run.get("status"),
            "total_records": len(results),
            "records": results,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_recurring_schedules_tool(client: OrbitBackendClient) -> dict[str, Any]:
    """
    Lists all active recurring scheduled automations and their next execution time.
    """
    try:
        data = await client.list_automations()
        items = data.get("items", [])
        scheduled = [
            {
                "id": a.get("id"),
                "objective": a.get("plan", {}).get("objective"),
                "frequency": a.get("plan", {}).get("frequency"),
                "schedule_time": a.get("plan", {}).get("schedule_time"),
                "timezone": a.get("plan", {}).get("timezone"),
                "next_run_at": a.get("next_run_at"),
            }
            for a in items
            if a.get("active") and a.get("plan", {}).get("frequency") != "once"
        ]
        return {"success": True, "total_scheduled": len(scheduled), "schedules": scheduled}
    except Exception as e:
        return {"success": False, "error": str(e)}
