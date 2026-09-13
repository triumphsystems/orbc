from typing import Any
from orbit.client import OrbitBackendClient


async def create_automation_tool(goal: str, client: OrbitBackendClient) -> dict[str, Any]:
    """
    Creates an autonomous web data workflow from a natural-language goal.
    The goal is interpreted into a domain-agnostic execution plan with dynamic extraction schema.

    Supports:
    - Multi-source discovery (open-web search, search APIs, and proxy search)
    - 2-hop autonomous navigation from listing/search pages to detail pages
    - Static threshold alerts ('min(price) < 400000', 'salary >= 150000')
    - Relative historical drop alerts ('alert me when lowest price drops by 10%')
    - Timezone-aware wall-clock schedules ('Every day at 8 AM WAT')

    Args:
        goal: Plain English objective.
    """
    try:
        data = await client.create_automation(goal)
        return {
            "success": True,
            "automation_id": data.get("id"),
            "objective": data.get("plan", {}).get("objective"),
            "domain": data.get("plan", {}).get("domain"),
            "search_query": data.get("plan", {}).get("search_query"),
            "frequency": data.get("plan", {}).get("frequency"),
            "condition": data.get("plan", {}).get("condition"),
            "extraction_schema": data.get("plan", {}).get("extraction_schema"),
            "raw_response": data,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_automations_tool(client: OrbitBackendClient) -> dict[str, Any]:
    """
    Lists all registered Orbit web-data automations and their active schedules.
    """
    try:
        data = await client.list_automations()
        items = data.get("items", [])
        summary = [
            {
                "id": a.get("id"),
                "objective": a.get("plan", {}).get("objective"),
                "domain": a.get("plan", {}).get("domain"),
                "frequency": a.get("plan", {}).get("frequency"),
                "active": a.get("active"),
                "next_run_at": a.get("next_run_at"),
            }
            for a in items
        ]
        return {"success": True, "total": len(summary), "automations": summary}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_automation_tool(automation_id: str, client: OrbitBackendClient) -> dict[str, Any]:
    """
    Gets details of a specific automation, including its dynamic extraction schema and schedule.

    Args:
        automation_id: The UUID of the automation.
    """
    try:
        data = await client.get_automation(automation_id)
        return {"success": True, "automation": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_automation_tool(automation_id: str, client: OrbitBackendClient) -> dict[str, Any]:
    """
    Deletes an automation and all its associated runs and results.

    Args:
        automation_id: The UUID of the automation to delete.
    """
    try:
        data = await client.delete_automation(automation_id)
        return {"success": True, "automation_id": automation_id, "message": data.get("message", "Automation deleted successfully")}
    except Exception as e:
        return {"success": False, "automation_id": automation_id, "error": str(e)}

