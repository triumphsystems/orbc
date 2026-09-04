from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Domain-agnostic application and pipeline settings."""

    model_config = SettingsConfigDict(env_file=(".env"), extra="ignore")

    app_env: str = "development"
    app_port: int = 8000
    log_level: str = "INFO"
    orbit_secret_key: str = ""
    allowed_origins: str = ""

    # LLM Engine
    llm_provider: str = "gemini"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    orchestrator_engine: str = "strands"

    # Web Data Retrieval & Discovery
    retrieval_api_key: str = ""
    retrieval_zone: str = ""
    retrieval_base_url: str = "https://api.brightdata.com"
    search_engine_api_key: str = ""
    search_engine_base_url: str = "https://serpapi.com/search.json"

    # Database & Scheduler
    database_url: str = "postgresql+psycopg2://orbit:orbit@localhost:5432/orbit"
    enable_scheduler: bool = True
    scheduler_secret: str = ""

    # Document Processing (Provider-Agnostic)
    document_converter_api_key: str = ""
    document_converter_base_url: str = "https://api.foxit.com/v1"
    document_dossier_api_key: str = ""
    document_dossier_base_url: str = "https://api.nutrient.io"
    document_redactor_api_key: str = ""
    document_redactor_base_url: str = "https://api.nutrient.io"
    document_template_api_key: str = ""
    document_template_base_url: str = "https://api.doctavian.com/v1"

    # Email Notifications (Provider-Agnostic Outbound Gateway)
    email_api_key: str = ""
    email_sender_address: str = "Orbit Alerts <alerts@orbit.dev>"
    email_base_url: str = "https://api.orbit.dev/v1/emails"

    # Cloud Object Storage (Provider-Agnostic: GCS / S3 / Local)
    storage_backend: str = "local"
    storage_bucket_name: str = "orbit-exports"
    storage_region: str = "us-central1"
    storage_project_id: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_endpoint_url: str = ""

    # Message Broker & Distributed Lock (Provider-Agnostic)
    event_broker_backend: str = "memory"
    broker_url: str = "redis://localhost:6379/0"
    broker_project_id: str = ""
    broker_key_prefix: str = "orb"

    # Unified Caching (Provider-Agnostic)
    cache_backend: str = "memory"
    cache_url: str = "redis://localhost:6379/1"
    cache_enabled: bool = True
    cache_default_ttl: int = 300

    # API Endpoint Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_goal_per_minute: int = 10
    rate_limit_run_per_minute: int = 20
    rate_limit_default_per_minute: int = 60

    # Global Run Concurrency Pool (Layer 3 Protection)
    max_concurrent_runs: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
