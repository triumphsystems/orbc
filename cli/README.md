# orbc 🛰️

A single-binary operator CLI for **Orbit — Autonomous Goal-Driven Web Data Operations**.

> *"Set the goal. Walk away."*

`orbc` provides command-line control over the Orbit daemon. It allows engineers to submit natural-language extraction goals, trigger on-demand pipeline executions, export structured datasets in table/CSV/JSON formats, inspect provenance DAGs, and monitor recurring schedules.

---

### Target Backend & Production Connection

By default, the CLI can connect to the public hosted production instance, a self-hosted cluster, or a local development daemon:

```bash
# 1. Connect to Hosted Production Daemon (Persistent Config)
orbc config set api_url https://orbit-wtsx.onrender.com

# 2. Connect to Hosted Production Daemon (One-off Command Flag)
orbc --api-url https://orbit-wtsx.onrender.com list

# 3. Connect via Environment Variable
export ORBC_API_URL=https://orbit-wtsx.onrender.com
```

---

## Installation & Build

### Build from Source

Requires Go 1.23+:

```bash
cd cli
go build -ldflags "-s -w -X github.com/leoemaxie/orbit/cli/internal/config.DefaultAPIURL=https://orbit-wtsx.onrender.com" -o bin/orbc ./cmd/orbc
# Output binary is generated at bin/orbc with production URL baked in
```

### Install to System PATH

```bash
# macOS / Linux
sudo cp bin/orbc /usr/local/bin/

# Windows (PowerShell running as Administrator)
Move-Item .\bin\orbc.exe C:\Windows\System32\
```

---

## Command Reference

### 1. Synthesize & Register a Goal

Submit a natural-language data requirement. Orbit compiles an execution plan, derives a typed schema, configures search parameters, and registers the schedule:

```bash
# Synthesize execution plan and register automation
orbc goal "Daily at 6 AM, monitor pricing, SKU availability, and inventory changes across top 5 enterprise cloud hardware vendors"

# Register automation and trigger an immediate initial run
orbc goal "Weekly on Monday, aggregate median tech compensation bands and level distributions across Tier 1 fintechs" --run

# Silent output mode (emits only the registered automation UUID)
ID=$(orbc goal "Every 4 hours, scan regional energy regulatory portals for tariff updates" -q)
```

### 2. Trigger Pipeline Execution

Execute an automation on demand outside its recurring schedule:

```bash
orbc run <automation_id>
```

### 3. List Registered Automations

```bash
# Formatted terminal table
orbc list

# Machine-readable JSON output
orbc list --json | jq .
```

### 4. Remove an Automation

Remove an automation and all its associated execution history:

```bash
orbc rm <automation_id>
# Alias: orbc delete <automation_id>
```

### 5. Inspect Execution History

View past runs, status codes, and record counts for an automation:

```bash
orbc runs <automation_id>
```

### 5. Inspect Run Telemetry & Provenance DAG

View end-to-end audit details for a specific run (sources discovered, retrieval status, validation outcome, LLM recovery steps, and condition match status):

```bash
orbc show <run_id>
```

### 6. Query & Export Extracted Data

Stream and export extracted data records from any run:

```bash
# Aligned terminal table with schema headers
orbc data <run_id>

# Export to CSV for spreadsheet / downstream analytics
orbc data <run_id> --format csv > cloud_hardware_pricing.csv

# Export schema-validated records to JSON
orbc data <run_id> --format json --valid-only | jq .
```

### 7. Manage Recurring Schedules

Inspect active daemon scheduler jobs and next firing timestamps:

```bash
orbc schedule list
```

### 8. Target Configuration

Configure the remote Orbit daemon endpoint:

```bash
# Set active daemon API URL
orbc config set api_url https://orbit.internal.corp:8000

# View current configuration
orbc config show
```

### 9. Version & Health Telemetry

```bash
orbc version
```
