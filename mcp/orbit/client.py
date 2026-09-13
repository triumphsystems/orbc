import asyncio
import json
import logging
from typing import Any, Optional
import httpx
from orbit.config import get_mcp_settings

logger = logging.getLogger("orbc.client")


class OrbitBackendClient:
    """Async HTTP client to communicate with the Orbit backend server."""

    def __init__(self, base_url: Optional[str] = None):
        settings = get_mcp_settings()
        self.base_url = (base_url or settings.orbit_api_url).rstrip("/")
        self.timeout = settings.request_timeout

    async def health(self) -> dict[str, Any]:
        """Check Orbit backend health status."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/api/v1/health")
            resp.raise_for_status()
            return resp.json()

    async def create_automation(self, goal: str) -> dict[str, Any]:
        """Interpret goal and create automation."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/automations",
                json={"goal": goal},
            )
            resp.raise_for_status()
            return resp.json()

    async def list_automations(self) -> dict[str, Any]:
        """List all automations."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{self.base_url}/api/v1/automations")
            resp.raise_for_status()
            return resp.json()

    async def get_automation(self, automation_id: str) -> dict[str, Any]:
        """Get single automation details."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{self.base_url}/api/v1/automations/{automation_id}")
            resp.raise_for_status()
            return resp.json()

    async def delete_automation(self, automation_id: str) -> dict[str, Any]:
        """Delete an automation."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.delete(f"{self.base_url}/api/v1/automations/{automation_id}")
            resp.raise_for_status()
            return resp.json()

    async def run_automation(self, automation_id: str) -> dict[str, Any]:
        """Trigger an execution run for an automation."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/v1/automations/{automation_id}/run")
            resp.raise_for_status()
            return resp.json()

    async def get_run(self, run_id: str) -> dict[str, Any]:
        """Get details, audit trail, and results of a specific run."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{self.base_url}/api/v1/runs/{run_id}")
            resp.raise_for_status()
            return resp.json()

    async def list_automation_runs(self, automation_id: str) -> list[dict[str, Any]]:
        """List past runs for an automation."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{self.base_url}/api/v1/automations/{automation_id}/runs")
            resp.raise_for_status()
            return resp.json()

    async def stream_run_and_wait(
        self,
        run_id: str,
        timeout: float = 300.0,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Connects to the live SSE telemetry stream of a run and streams events until completion.
        Ensures long-running agentic execution completes reliably with live progress reports.
        """
        url = f"{self.base_url}/api/v1/runs/{run_id}/stream"
        last_snapshot: dict[str, Any] = {}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("GET", url, headers={"Accept": "text/event-stream"}) as response:
                    response.raise_for_status()

                    current_event = "message"
                    data_lines: list[str] = []

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if line.startswith("event:"):
                            current_event = line[6:].strip()
                        elif line.startswith("data:"):
                            data_lines.append(line[5:].strip())
                        elif not line and data_lines:
                            raw_data = "\n".join(data_lines)
                            data_lines = []
                            try:
                                payload = json.loads(raw_data)
                                last_snapshot = payload
                                if progress_callback and callable(progress_callback):
                                    if asyncio.iscoroutinefunction(progress_callback):
                                        await progress_callback(current_event, payload)
                                    else:
                                        progress_callback(current_event, payload)

                                if current_event == "complete" or payload.get("status") in ("verified", "failed"):
                                    return payload
                            except Exception:
                                pass
        except Exception as err:
            logger.warning(f"SSE stream interrupted for run {run_id}, falling back to poll: {err}")

        if not last_snapshot or last_snapshot.get("status") not in ("verified", "failed"):
            return await self.get_run(run_id)
        return last_snapshot
