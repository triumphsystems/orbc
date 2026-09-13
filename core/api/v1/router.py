from fastapi import APIRouter
from core.api.v1.automations import router as automations_router
from core.api.v1.health import router as health_router
from core.api.v1.runs import router as runs_router
from core.api.v1.scheduler import router as scheduler_router
from core.api.v1.templates import router as templates_router
from core.api.v1.workflows import router as workflows_router

v1_router = APIRouter()
v1_router.include_router(health_router)
v1_router.include_router(automations_router)
v1_router.include_router(runs_router)
v1_router.include_router(scheduler_router)
v1_router.include_router(workflows_router)
v1_router.include_router(templates_router)
