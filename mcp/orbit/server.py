import asyncio
import logging
from typing import Any

try:
    from mcp.server.mcpserver import MCPServer
except (ImportError, ModuleNotFoundError):
    from mcp.server.fastmcp import FastMCP as MCPServer

from orbit.client import OrbitBackendClient
from orbit.prompts.templates import AUDIT_FAILURE_PROMPT, WORKFLOW_DESIGN_PROMPT
from orbit.resources.provider import OrbitResourceProvider
from orbit.tools.automations import (
    create_automation_tool,
    delete_automation_tool,
    get_automation_tool,
    list_automations_tool,
)
from orbit.tools.execution import execute_goal_tool, run_automation_tool
from orbit.tools.inspection import (
    get_run_details_tool,
    list_recurring_schedules_tool,
    query_extracted_data_tool,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orbc.server")

# Initialize MCP Server with tool name 'orbc'
mcp = MCPServer("orbc")
client = OrbitBackendClient()
resource_provider = OrbitResourceProvider(client)


# ─────────────────────────────────────────────────────────────
# TOOLS (orbc)
# ─────────────────────────────────────────────────────────────

@mcp.tool()
async def create_automation(goal: str) -> dict[str, Any]:
    """
    Creates an autonomous web data workflow from a natural language goal.
    The goal is interpreted into a domain-agnostic execution plan with a dynamic extraction schema.

    Args:
        goal: Plain English objective (e.g. 'Daily at 6 AM, monitor pricing and availability across cloud GPU providers')
    """
    return await create_automation_tool(goal, client)


@mcp.tool()
async def run_automation(automation_id: str) -> dict[str, Any]:
    """
    Triggers an on-demand autonomous run for a registered automation.
    Executes the full agent loop: discovery -> retrieval -> extraction -> validation -> condition evaluation -> verification.

    Args:
        automation_id: The UUID of the automation to run.
    """
    return await run_automation_tool(automation_id, client)


@mcp.tool()
async def execute_goal(goal: str) -> dict[str, Any]:
    """
    One-shot execution: Interprets a natural language goal, creates an automation,
    immediately executes the full agent loop, and returns the extracted structured records.

    Args:
        goal: Natural language web data objective.
    """
    return await execute_goal_tool(goal, client)


@mcp.tool()
async def list_automations() -> dict[str, Any]:
    """
    Lists all registered Orbit web-data automations and their active schedules.
    """
    return await list_automations_tool(client)


@mcp.tool()
async def get_automation(automation_id: str) -> dict[str, Any]:
    """
    Gets details of a specific automation, including its dynamic extraction schema and schedule.

    Args:
        automation_id: The UUID of the automation.
    """
    return await get_automation_tool(automation_id, client)


@mcp.tool()
async def delete_automation(automation_id: str) -> dict[str, Any]:
    """
    Deletes an automation and all its associated historical runs and extracted records.

    Args:
        automation_id: The UUID of the automation to delete.
    """
    return await delete_automation_tool(automation_id, client)



@mcp.tool()
async def get_run_details(run_id: str) -> dict[str, Any]:
    """
    Retrieves full execution audit trail, provenance (sources discovered, pages retrieved),
    reasoning logs, and validation errors for a specific run.

    Args:
        run_id: The UUID of the run to inspect.
    """
    return await get_run_details_tool(run_id, client)


@mcp.tool()
async def query_extracted_data(run_id: str, valid_only: bool = True) -> dict[str, Any]:
    """
    Queries and filters extracted structured records for a specific run.

    Args:
        run_id: The UUID of the run.
        valid_only: If True, returns only records that passed dynamic schema validation.
    """
    return await query_extracted_data_tool(run_id, valid_only, client)


@mcp.tool()
async def list_recurring_schedules() -> dict[str, Any]:
    """
    Lists all active recurring scheduled automations and their next execution times.
    """
    return await list_recurring_schedules_tool(client)


# ─────────────────────────────────────────────────────────────
# RESOURCES (orbc://)
# ─────────────────────────────────────────────────────────────

@mcp.resource("orbc://automations")
async def get_automations_resource() -> str:
    """Resource returning JSON list of all registered automations."""
    return await resource_provider.list_automations_resource()


@mcp.resource("orbc://automations/{automation_id}")
async def get_single_automation_resource(automation_id: str) -> str:
    """Resource returning JSON representation of an automation specification."""
    return await resource_provider.get_automation_resource(automation_id)


@mcp.resource("orbc://runs/{run_id}")
async def get_single_run_resource(run_id: str) -> str:
    """Resource returning JSON execution log and records for a run."""
    return await resource_provider.get_run_resource(run_id)


# ─────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────

@mcp.prompt()
def create_web_data_workflow() -> str:
    """Guided prompt for formulating an autonomous web data goal with orbc."""
    return WORKFLOW_DESIGN_PROMPT


@mcp.prompt()
def audit_run_failure(run_id: str) -> str:
    """Diagnostic prompt for investigating and explaining a failed run."""
    return AUDIT_FAILURE_PROMPT.format(run_id=run_id)


import argparse

# Export ASGI app for running directly with `uvicorn orbit.server:app` in container / remote deployments
if hasattr(mcp, "sse_app"):
    try:
        app = mcp.sse_app()
    except Exception:
        app = None
else:
    app = None


def main():
    """Main entrypoint supporting local stdio and remote SSE MCP transports."""
    from orbit.config import get_mcp_settings

    parser = argparse.ArgumentParser(description="Orbit MCP Server (orbc)")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=None,
        help="Transport protocol: 'stdio' for local client pipes, 'sse' for remote HTTP/SSE (default: stdio or MCP_TRANSPORT)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host interface for SSE server (default: 0.0.0.0 or MCP_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for SSE server (default: 8001 or MCP_PORT)",
    )
    args, _ = parser.parse_known_args()

    settings = get_mcp_settings()
    transport = (args.transport or settings.mcp_transport or "stdio").lower()
    host = args.host or settings.mcp_host or "0.0.0.0"
    port = args.port or settings.mcp_port or 8001

    if hasattr(mcp, "settings"):
        for attr in ("host", "bind_host"):
            if hasattr(mcp.settings, attr):
                try:
                    setattr(mcp.settings, attr, host)
                except Exception:
                    pass
        if hasattr(mcp.settings, "port"):
            try:
                mcp.settings.port = port
            except Exception:
                pass

    if transport == "sse":
        logger.info(f"Starting Orbit MCP Server over SSE on http://{host}:{port}/sse ...")
        if hasattr(mcp, "run"):
            try:
                mcp.run(transport="sse")
            except TypeError:
                try:
                    mcp.run(transport="sse", host=host, port=port)
                except TypeError:
                    mcp.run()
        elif hasattr(mcp, "run_sse_async"):
            import anyio
            anyio.run(mcp.run_sse_async)
    else:
        logger.info("Starting Orbit MCP Server over stdio ...")
        if hasattr(mcp, "run"):
            try:
                mcp.run(transport="stdio")
            except TypeError:
                mcp.run()
        elif hasattr(mcp, "run_stdio_async"):
            import anyio
            anyio.run(mcp.run_stdio_async)


if __name__ == "__main__":
    main()
