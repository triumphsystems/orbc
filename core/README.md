# Orbit Core Engine

The backend execution engine, agentic reasoning pipeline, scheduler daemon, and REST API for **Orbit — Autonomous Goal-Driven Web Data Operations**.

---

## Overview

Orbit Core is the orchestrator and execution daemon of the Orbit platform. It handles the complete lifecycle of natural-language objective compilation, web data extraction, verification, and recurring scheduling:

- **Goal Interpretation & Execution Planning**: Compiles natural-language requirements into strongly typed JSON schemas, search vectors, recurring Cron schedules, and condition triggers via LLM reasoning.
- **Autonomous Multi-Source Discovery**: Discovers authoritative target endpoints across search APIs, web indexes, and domain heuristics.
- **Resilient Content Retrieval**: Manages resilient proxy rotation (including Bright Data Web Unlocker) to bypass dynamic anti-bot protection and JavaScript rendering walls.
- **Schema-Driven Extraction & Validation**: Extracts structured records matching derived domain schemas and validates data types, required fields, and anomaly thresholds.
- **Agentic Self-Healing Loop**: Analyzes retrieval and parsing failures, diagnoses empty result sets or DOM structural mutations, and dynamically recalculates discovery parameters.
- **Condition Triggers & Webhook Dispatch**: Evaluates scalar and aggregate rules (e.g. `min(price_per_hour) < 2.50` or `status == 'critical'`) and dispatches structured event payloads to configured webhooks.
- **Scheduled Pipeline Daemon**: Manages recurring execution intervals using APScheduler with concurrency control, state persistence in PostgreSQL, and full execution provenance trails.

---

## Architecture & Module Structure

```text
core/
├── adapters/         # Pluggable outputs & notification sinks (Slack, Webhooks, File sinks)
├── agent/            # Goal Interpreter, Condition Evaluator, Agent Brain, Orchestrator
├── api/              # FastAPI v1 router & endpoints (automations, runs, health)
├── config/           # Pydantic Settings & environment configuration
├── db/               # SQLAlchemy ORM models & database session management
├── events/           # Async in-process Event Bus & event definitions
├── llm/              # LLM client abstractions & prompt templates
├── models/           # Domain schemas, DynamicExtractionSchema, ExecutionPlan
├── notifications/    # Alerting service (Webhooks & Structured Logs)
├── pipeline/         # Discovery, Retrieval, Extraction, and Validation stages
│   ├── discovery/    # Multi-source search & composite URL discovery
│   ├── extraction/   # Schema-driven LLM structured data extractor
│   ├── retrieval/    # Resilient proxy client & link extraction
│   └── validation/   # JSONSchema validation & statistical anomaly detection
├── scheduler/        # APScheduler recurring execution engine & cron helpers
└── app.py            # FastAPI application factory and lifecycle manager
```

---

## Getting Started

### 1. Prerequisites

- Python 3.10+
- PostgreSQL 15+ (local or Docker container)
- Redis
- Platform API Keys (Refer to [`.env.example`](.env.example))

### 2. Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# Install core package with development dependencies
pip install -e ".[dev]"
```

### 3. Environment Configuration

Create a `.env` file by copying the template from [`.env.example`](.env.example):

```bash
# Windows (PowerShell):
Copy-Item .env.example .env

# macOS / Linux:
cp .env.example .env
```

#### Mandatory Environment Variables

Ensure the following essential variables are configured in your `.env` file:

| Variable | Description | Example / Supported Values |
| :--- | :--- | :--- |
| `DATABASE_URL` | Relational database connection string (PostgreSQL or local SQLite) | `postgresql+psycopg2://orbit:orbit@localhost:5432/orbit` or `sqlite:///./orbit.db` |
| `LLM_PROVIDER` | LLM engine provider discriminator | `gemini` \| `openrouter` \| `openai` |
| `LLM_API_KEY` | API authentication key for the chosen LLM provider | `your-api-key` |
| `LLM_MODEL` | Target foundation model for plan synthesis and schema extraction | `gemini-2.5-flash`, `google/gemini-2.5-flash`, `gpt-4o-mini` |
| `RETRIEVAL_API_KEY` | Web unlocker proxy / retrieval service API key | `your-proxy-unlocker-api-key` |
| `BROKER_URL` | Message broker & lock connection URL (when `EVENT_BROKER_BACKEND=redis`) | `redis://localhost:6379/0` |
| `BROKER_PROJECT_ID`| Google Cloud Project ID (when `EVENT_BROKER_BACKEND=pubsub`) | `your-gcloud-project-id` |

> Refer to [`.env.example`](.env.example) for complete configuration options (including search engines, document parsers, S3 storage, and notification sinks).

### 4. Run the Server

```bash
uvicorn core.app:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI Specification**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- **Health Check Probe**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## REST API Reference

### 1. Synthesize and Register an Automation

Submit a natural-language data requirement to compile an autonomous execution plan:

`POST /api/v1/automations`

```json
{
  "goal": "Daily at 6 AM, monitor pricing, SKU availability, and instance specs across top enterprise cloud hardware vendors and alert if H100 spot rate drops below $2.80/hr"
}
```

**Response:**
```json
{
  "id": "7b8c9d01-e234-4567-89ab-cdef01234567",
  "raw_goal": "Daily at 6 AM, monitor pricing, SKU availability, and instance specs across top enterprise cloud hardware vendors and alert if H100 spot rate drops below $2.80/hr",
  "plan": {
    "objective": "Monitor enterprise cloud hardware pricing, instance specs, and availability daily; alert on H100 spot < $2.80/hr",
    "domain": "cloud_infrastructure",
    "search_query": "enterprise cloud GPU instance pricing H100 spot on-demand",
    "source_hints": ["lambda.com", "coreweave.com", "runpod.io", "vast.ai"],
    "geography": "Global",
    "country_code": "us",
    "extraction_schema": {
      "entity_name": "cloud_gpu_sku",
      "fields": [
        {"name": "provider", "type": "string", "required": true},
        {"name": "gpu_model", "type": "string", "required": true},
        {"name": "gpu_count", "type": "integer", "required": true},
        {"name": "vram_per_gpu_gb", "type": "integer", "required": true},
        {"name": "price_per_hour", "type": "number", "required": true},
        {"name": "pricing_tier", "type": "string", "enum_values": ["spot", "on_demand", "reserved"]},
        {"name": "availability", "type": "string", "enum_values": ["available", "limited", "out_of_stock"]}
      ]
    },
    "frequency": "daily",
    "schedule_time": "06:00",
    "timezone": "UTC",
    "condition": "min(price_per_hour) < 2.80"
  },
  "active": true,
  "created_at": "2026-08-24T06:00:00Z"
}
```

### 2. Trigger an Immediate Run

`POST /api/v1/automations/{automation_id}/run`

**Response:**
```json
{
  "id": "run-8f92a10b-4c5e",
  "status": "verified",
  "sources_found": [
    "https://lambda.com/service/gpu-cloud",
    "https://runpod.io/pricing"
  ],
  "pages_retrieved": [
    "https://lambda.com/service/gpu-cloud",
    "https://runpod.io/pricing"
  ],
  "extracted_count": 8,
  "validated_count": 8,
  "condition_matched": true,
  "condition_message": "Aggregation min(price_per_hour) = 2.49 vs target < 2.80 -> Matched: True",
  "results": [
    {
      "url": "https://runpod.io/pricing",
      "data": {
        "provider": "RunPod",
        "gpu_model": "NVIDIA H100 80GB SXM5",
        "gpu_count": 1,
        "vram_per_gpu_gb": 80,
        "price_per_hour": 2.49,
        "pricing_tier": "spot",
        "availability": "available"
      },
      "valid": true
    }
  ]
}
```

### 3. Pipeline Telemetry & Endpoints

- `GET /api/v1/automations` — List all registered automations and active schedules.
- `GET /api/v1/automations/{id}` — Retrieve the synthesized plan, schema, and schedule details.
- `GET /api/v1/automations/{id}/runs` — Retrieve historical execution runs and success metrics.
- `GET /api/v1/runs/{id}` — Retrieve complete run telemetry, DAG stages, LLM reasoning traces, and audit logs.
- `GET /api/v1/runs/{id}/results` — Query and export structured records with schema validity filtering.

---

## Testing

Execute the test suite via pytest:

```bash
# Run unit and integration tests
pytest

# Run with verbose output and coverage report
pytest -v --cov=core
```
