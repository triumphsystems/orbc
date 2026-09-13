import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from core import __version__
from core.api.v1.router import v1_router
from core.config.settings import get_settings
from core.db.orm import (  # noqa: F401
    AdapterConfig,
    Automation,
    Result,
    Run,
    Template,
    WorkflowPipeline,
)
from core.db.session import Base, cleanup_stale_runs, engine, ensure_schema_columns
from core.scheduler.service import scheduler_service

logger = logging.getLogger("core.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        ensure_schema_columns(engine)
        cleanup_stale_runs()
        logger.info("Database schemas, tables, and stale run recovery verified successfully.")
    except Exception as e:
        logger.warning(
            "Database connection failed during startup (%s). Ensure PostgreSQL is running on port 5432 or set DATABASE_URL=sqlite:///./orbit.db in your .env file.",
            e,
        )

    settings = get_settings()
    if settings.enable_scheduler:
        scheduler_service.start(check_interval_seconds=30)
    yield
    if settings.enable_scheduler:
        scheduler_service.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Orbit",
        description="Autonomous Goal-Driven Web Data Operations",
        version=__version__,
        lifespan=lifespan,
    )

    settings = get_settings()
    env_origins = [orig.strip() for orig in (settings.allowed_origins or "").split(",") if orig.strip()]
    default_dev_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    cors_origins = list(dict.fromkeys(default_dev_origins + env_origins))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database operational error encountered: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "The operation could not be completed. Please retry your request shortly."},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code >= 500:
            logger.error("Internal server error (HTTP %d): %s", exc.status_code, exc.detail)
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": "An internal server error occurred while processing your request. Please try again later."},
                headers=exc.headers,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred while processing your request. Please try again shortly."},
        )

    app.include_router(v1_router, prefix="/api/v1")

    @app.get("/", tags=["Health"])
    def root():
        return {"status": "ok", "service": "orbit-core", "version": __version__}

    return app


app = create_app()
