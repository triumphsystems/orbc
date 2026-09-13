from core import __version__
from core.config.settings import get_settings
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.app_env,
        "scheduler_enabled": settings.enable_scheduler,
    }
