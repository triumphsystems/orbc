import json
from typing import Any
from orbit.client import OrbitBackendClient


class OrbitResourceProvider:
    """Provides dynamic MCP resources for Orbit data models."""

    def __init__(self, client: OrbitBackendClient):
        self.client = client

    async def list_automations_resource(self) -> str:
        """Resource content for orbc://automations"""
        data = await self.client.list_automations()
        return json.dumps(data, indent=2)

    async def get_automation_resource(self, automation_id: str) -> str:
        """Resource content for orbc://automations/{automation_id}"""
        data = await self.client.get_automation(automation_id)
        return json.dumps(data, indent=2)

    async def get_run_resource(self, run_id: str) -> str:
        """Resource content for orbc://runs/{run_id}"""
        data = await self.client.get_run(run_id)
        return json.dumps(data, indent=2)
