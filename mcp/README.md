# Orbit MCP Server 🛰️

**Model Context Protocol (MCP) Server for Orbit Autonomous Web Data Operations**

The Orbit MCP server connects AI coding assistants and LLM agent environments (Claude Desktop, Cursor, Antigravity, VS Code, Cline, Windsurf, Zed) with Orbit's autonomous data extraction and scheduling engine.

Through standard MCP tools, resources, and prompts, AI agents can formulate data collection objectives, execute ad-hoc and recurring extraction pipelines, query validated records, inspect failure recovery steps, and audit execution provenance directly within their development workflows.

---

## Exposed MCP Capabilities

### 1. Tools

| Tool | Parameters | Description |
|---|---|---|
| `create_automation` | `goal: str` | Interprets a natural-language data requirement into an `ExecutionPlan` with a derived typed JSON schema and schedule. |
| `run_automation` | `automation_id: str` | Triggers the complete agentic pipeline on demand (discovery → proxy retrieval → schema extraction → anomaly validation → condition evaluation). |
| `execute_goal` | `goal: str` | **One-shot pipeline execution**: Interprets the goal, creates the plan, executes extraction, and returns validated records in a single tool call. |
| `list_automations` | *none* | Lists all registered data automations and active schedules. |
| `get_automation` | `automation_id: str` | Retrieves the dynamic extraction schema, objective, and schedule details for a specific automation. |
| `delete_automation` | `automation_id: str` | Deletes an automation and all its associated historical runs and records. |
| `get_run_details` | `run_id: str` | Returns end-to-end execution audit logs, discovered endpoints, HTTP retrieval states, and agent self-healing decisions. |
| `query_extracted_data` | `run_id: str`, `valid_only: bool = true` | Queries extracted structured records with optional validation filtering. |
| `list_recurring_schedules` | *none* | Lists all active recurring scheduler jobs and next scheduled execution timestamps. |

### 2. Resources (`orbc://`)

| URI Pattern | Description |
|---|---|
| `orbc://automations` | Live JSON index of all registered automations and active schedules. |
| `orbc://automations/{automation_id}` | Automation specification JSON (objective, domain, extraction schema, schedule). |
| `orbc://runs/{run_id}` | Full run audit trail, DAG step telemetry, and validated structured records. |

### 3. Prompts

| Prompt | Description |
|---|---|
| `create_web_data_workflow` | Interactive prompt guiding the agent to formulate robust, production-grade autonomous data extraction pipelines. |
| `audit_run_failure` | Diagnostic prompt for auditing pipeline runs, analyzing Agent Brain self-correction logs, and recommending strategy fixes. |

---

## Installation & Running

Ensure the Orbit Core daemon is running (default `http://127.0.0.1:8000`).

### 1. Install the MCP Package

```bash
cd mcp
pip install -e .
```

### 2. Run Modes

#### Local Stdio Mode (Default)

```bash
# Option A: Python module execution
python -m orbit.server

# Option B: Installed binary entrypoint
orbc-mcp
```

#### Remote SSE Mode (HTTP / Server-Sent Events)

For hosting Orbit MCP remotely over HTTP/SSE:

```bash
# Option A: CLI flag
python -m orbit.server --transport sse --host 0.0.0.0 --port 8001
# or
orbc-mcp --transport sse --host 0.0.0.0 --port 8001

# Option B: Environment variables
MCP_TRANSPORT=sse MCP_HOST=0.0.0.0 MCP_PORT=8001 python -m orbit.server

# Option C: Production ASGI server (Uvicorn / Docker)
uvicorn orbit.server:app --host 0.0.0.0 --port 8001
```

Once running, the remote SSE endpoint is accessible at:
* SSE Stream: `http://<host>:8001/sse`
* Message POST endpoint: `http://<host>:8001/messages/`

---

## Client Configurations

### Antigravity / Cursor

Add to your MCP Settings or `mcp_config.json`:

**Local Stdio (Windows):**
```json
{
  "mcpServers": {
    "orbit": {
      "command": "E:\\Documents\\Projects\\orbit\\mcp\\venv\\Scripts\\python.exe",
      "args": ["-m", "orbit.server"],
      "cwd": "E:\\Documents\\Projects\\orbit\\mcp",
      "env": {
        "ORBIT_API_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

**Local Stdio (Linux / macOS):**
```json
{
  "mcpServers": {
    "orbit": {
      "command": "/path/to/orbit/mcp/venv/bin/python",
      "args": ["-m", "orbit.server"],
      "cwd": "/path/to/orbit/mcp",
      "env": {
        "ORBIT_API_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

**Remote SSE Mode:**
```json
{
  "mcpServers": {
    "orbit": {
      "url": "http://127.0.0.1:8001/sse"
    }
  }
}
```

### Claude Desktop & VS Code (Cline / Roo-Code)

```json
{
  "mcpServers": {
    "orbit": {
      "command": "E:\\Documents\\Projects\\orbit\\mcp\\venv\\Scripts\\python.exe",
      "args": ["-m", "orbit.server"],
      "cwd": "E:\\Documents\\Projects\\orbit\\mcp",
      "env": {
        "ORBIT_API_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

---

## Testing

Execute the MCP test suite:

```bash
pytest mcp/tests/
```
