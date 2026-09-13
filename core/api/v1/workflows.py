from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows & Adapters"])


class AdapterTopologyOut(BaseModel):
    id: str
    label: str
    category: str
    mode: str = "both"
    engine: str = ""
    icon_name: str = Field(alias="iconName")
    description: str
    status: str
    config: dict[str, Any]

    model_config = {"populate_by_name": True}


class WorkflowDeployPayload(BaseModel):
    nodes: list[dict[str, Any]]


class WorkflowDeployResponse(BaseModel):
    status: str
    message: str
    deployed_at: str


class TestConnectionPayload(BaseModel):
    adapter_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


class SaveAdapterConfigPayload(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class SaveAdapterConfigResponse(BaseModel):
    status: str
    adapter_id: str
    message: str
    saved_at: str


@router.post("/adapters/{adapter_id}/config", response_model=SaveAdapterConfigResponse)
@router.put("/adapters/{adapter_id}/config", response_model=SaveAdapterConfigResponse)
def save_adapter_config(adapter_id: str, payload: SaveAdapterConfigPayload) -> SaveAdapterConfigResponse:
    """Persists configuration parameters and credentials for a workflow adapter."""
    from datetime import datetime, timezone

    WorkflowService.save_adapter_config(adapter_id, payload.config)
    return SaveAdapterConfigResponse(
        status="saved",
        adapter_id=adapter_id,
        message=f"Configuration for adapter '{adapter_id}' saved successfully.",
        saved_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/pipeline", response_model=list[dict[str, Any]])
def get_deployed_pipeline() -> list[dict[str, Any]]:
    """Returns the current deployed pipeline nodes configured by the user."""
    return WorkflowService.get_deployed_pipeline()


@router.get("/topology", response_model=list[AdapterTopologyOut])
def get_workflow_topology() -> list[dict[str, Any]]:
    """Returns live adapter configurations across managed, custom, and hybrid modes."""
    return WorkflowService.get_adapter_topology()


@router.post("/deploy", response_model=WorkflowDeployResponse)
def deploy_workflow(payload: WorkflowDeployPayload) -> WorkflowDeployResponse:
    """Validates and deploys the adapter pipeline configuration."""
    from datetime import datetime, timezone

    WorkflowService.deploy_pipeline(payload.nodes)
    return WorkflowDeployResponse(
        status="deployed",
        message=f"Pipeline updated with {len(payload.nodes)} active adapter stages.",
        deployed_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_adapter_connection(payload: TestConnectionPayload) -> TestConnectionResponse:
    """Securely tests connectivity for a specific adapter."""
    success, message = await WorkflowService.test_adapter_connection(payload.adapter_id, payload.config)
    return TestConnectionResponse(success=success, message=message)
