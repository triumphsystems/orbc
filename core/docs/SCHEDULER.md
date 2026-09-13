# Orbit Cloud-Native Scheduler Guide 🛰️

Orbit supports a **dual-mode scheduler architecture**:
1. **Development Mode (Local / In-Process)**: Uses an internal APScheduler loop bundled directly in FastAPI (`ENABLE_SCHEDULER=true`).
2. **Production Mode (Cloud-Native / Stateless)**: Runs Orbit as a stateless API container (`ENABLE_SCHEDULER=false`) and triggers recurring automations via a universal cloud webhook (`POST /api/v1/scheduler/trigger-due`).

---

## 1. Webhook Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/scheduler/trigger-due` | Finds all active automations where `next_run_at <= now`, triggers them asynchronously, and calculates their next execution timestamp. |
| `POST` | `/api/v1/scheduler/tick` | Alias for `/trigger-due`. |
| `GET`  | `/api/v1/scheduler/status` | Returns a list of all active schedules, timezones, and next execution timestamps. |

### Optional Authentication Header
If `SCHEDULER_SECRET` is set in your environment:
- Include either header:
  - `X-Scheduler-Secret: <YOUR_SECRET>`
  - `Authorization: Bearer <YOUR_SECRET>`

---

## 2. Cloud Provider Configurations

### Google Cloud (Cloud Run + Cloud Scheduler)

```bash
gcloud scheduler jobs create http orbit-scheduler-tick \
  --schedule="*/15 * * * *" \
  --uri="https://YOUR-APP.run.app/api/v1/scheduler/trigger-due" \
  --http-method=POST \
  --headers="X-Scheduler-Secret=YOUR_SECRET" \
  --time-zone="UTC"
```

---

### Render.com

Add a Cron Job in your `render.yaml` or Dashboard:

```yaml
services:
  - type: cron
    name: orbit-scheduler
    env: python
    schedule: "*/15 * * * *"
    command: "curl -s -X POST https://YOUR-APP.onrender.com/api/v1/scheduler/trigger-due -H \"X-Scheduler-Secret: $SCHEDULER_SECRET\""
```

---

### AWS (EventBridge Scheduler)

```bash
aws scheduler create-schedule \
  --name "orbit-scheduler-tick" \
  --schedule-expression "rate(15 minutes)" \
  --target '{
    "Arn": "arn:aws:scheduler:::aws-sdk:http:request",
    "Input": "{\"Uri\": \"https://YOUR-API-GATEWAY/api/v1/scheduler/trigger-due\", \"Method\": \"POST\", \"Headers\": {\"X-Scheduler-Secret\": \"YOUR_SECRET\"}}"
  }' \
  --flexible-time-window '{"Mode": "OFF"}'
```

---

### Fly.io

Add to your `fly.toml`:

```toml
[[services]]
  http_checks = []
  internal_port = 8080
  protocol = "tcp"

[deploy]
  release_command = "python -c 'from core.db.session import Base, engine; Base.metadata.create_all(bind=engine)'"
```

Create a scheduled machine or use an external ping service.

---

### Railway

Add a cron trigger to ping the endpoint every 15 minutes, or use a lightweight worker service executing:

```bash
while true; do curl -s -X POST https://YOUR-APP.up.railway.app/api/v1/scheduler/trigger-due -H "X-Scheduler-Secret: $SCHEDULER_SECRET"; sleep 900; done
```

---

### GitHub Actions (Zero Extra Infrastructure)

Create `.github/workflows/orbit-scheduler.yml`:

```yaml
name: Orbit Scheduler Tick
on:
  schedule:
    - cron: '*/15 * * * *'
  workflow_dispatch:

jobs:
  tick:
    runs-on: ubuntu-latest
    steps:
      - name: Ping Orbit Scheduler Hook
        run: |
          curl -f -s -X POST "${{ secrets.ORBIT_API_URL }}/scheduler/trigger-due" \
            -H "X-Scheduler-Secret: ${{ secrets.SCHEDULER_SECRET }}"
```

---

## 3. Local Development

In local development (`.env`):
```bash
APP_ENV="development"
ENABLE_SCHEDULER=true
```
When `ENABLE_SCHEDULER=true`, Orbit automatically starts its in-process scheduler and checks the database every 30 seconds without needing any external cloud triggers.
