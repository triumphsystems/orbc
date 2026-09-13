import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from core.config.settings import get_settings

logger = logging.getLogger("core.db.session")

settings = get_settings()

db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
engine_kwargs: dict = {
    "pool_pre_ping": True,
}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    if "postgresql" in db_url or "postgres" in db_url:
        connect_args = {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "connect_timeout": 15,
        }
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

Base = declarative_base()


def ensure_schema_columns(eng):
    """Safely adds missing columns and migrates mismatched column types in existing tables."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(eng)
        table_names = inspector.get_table_names()

        if "results" in table_names:
            columns = [c["name"] for c in inspector.get_columns("results")]
            with eng.begin() as conn:
                if "valid" not in columns:
                    conn.execute(text("ALTER TABLE results ADD COLUMN valid BOOLEAN DEFAULT TRUE"))
                if "validation_errors" not in columns:
                    conn.execute(text("ALTER TABLE results ADD COLUMN validation_errors JSON"))
                if "created_at" not in columns:
                    conn.execute(text("ALTER TABLE results ADD COLUMN created_at TIMESTAMP"))

        if "runs" in table_names:
            runs_cols = {c["name"]: c for c in inspector.get_columns("runs")}
            with eng.begin() as conn:
                # 1. Check pages_retrieved (migrate from INTEGER to JSON if needed)
                if "pages_retrieved" not in runs_cols:
                    conn.execute(text("ALTER TABLE runs ADD COLUMN pages_retrieved JSON"))
                elif eng.dialect.name == "postgresql":
                    col_type = str(runs_cols["pages_retrieved"]["type"]).upper()
                    if "INT" in col_type:
                        logger.info("Migrating runs.pages_retrieved from INTEGER to JSON...")
                        conn.execute(
                            text(
                                "ALTER TABLE runs ALTER COLUMN pages_retrieved TYPE JSON "
                                "USING (CASE WHEN pages_retrieved IS NULL THEN NULL ELSE '[]'::json END)"
                            )
                        )

                # 2. Check sources_found (migrate from INTEGER to JSON if needed)
                if "sources_found" not in runs_cols:
                    conn.execute(text("ALTER TABLE runs ADD COLUMN sources_found JSON"))
                elif eng.dialect.name == "postgresql":
                    col_type = str(runs_cols["sources_found"]["type"]).upper()
                    if "INT" in col_type:
                        logger.info("Migrating runs.sources_found from INTEGER to JSON...")
                        conn.execute(
                            text(
                                "ALTER TABLE runs ALTER COLUMN sources_found TYPE JSON "
                                "USING (CASE WHEN sources_found IS NULL THEN NULL ELSE '[]'::json END)"
                            )
                        )

                # 3. Check other audit trail columns
                if "reasoning_log" not in runs_cols:
                    conn.execute(text("ALTER TABLE runs ADD COLUMN reasoning_log JSON"))
                if "condition_matched" not in runs_cols:
                    conn.execute(text("ALTER TABLE runs ADD COLUMN condition_matched BOOLEAN"))
                if "condition_message" not in runs_cols:
                    conn.execute(text("ALTER TABLE runs ADD COLUMN condition_message TEXT"))
    except Exception as e:
        logger.warning("Schema auto-migration check encountered an error: %s", e)


def cleanup_stale_runs():
    """Resets orphaned runs from previous server sessions/crashes to failed state."""
    try:
        from datetime import datetime, timezone
        from core.db.orm import Run
        from core.models.enums import RunStatus
        with SessionLocal() as db:
            stale_runs = (
                db.query(Run)
                .filter(Run.status.notin_([RunStatus.verified, RunStatus.failed]))
                .all()
            )
            if stale_runs:
                for r in stale_runs:
                    r.status = RunStatus.failed
                    r.error = "Run interrupted by server restart or unexpected crash."
                    r.finished_at = datetime.now(timezone.utc)
                db.commit()
    except Exception:
        pass


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
