# Orbit Web Application

The Orbit Web Application is the operational mission control console and telemetry interface for the Orbit autonomous data operations platform. Built for engineering and data teams, it provides real-time visibility into pipeline executions, schema derivation, data lineage DAGs, and anomaly verification.

---

## Technical Stack

- **Framework**: SvelteKit with Svelte 5 Runes (`$state`, `$derived`, `$effect`)
- **Styling**: Tailwind CSS v4
- **Typography**: Plus Jakarta Sans (UI Chrome) & JetBrains Mono (Telemetry & Schema types)
- **Icons**: `@lucide/svelte`
- **Deployment Adapter**: `@sveltejs/adapter-vercel`
- **Package Manager**: `pnpm`

---

## Core Capabilities

- **Operator Mission Studio**: Submit natural-language data extraction objectives and inspect real-time synthesized execution plans, Cron intervals, and typed JSON schemas.
- **Execution Lineage & Provenance DAG**: Visual DAG tracing each stage of the data pipeline (Goal Synthesis → Source Discovery → Proxy Retrieval → Schema Extraction → Anomaly Verification → Condition Evaluation) with slide-over telemetry and raw log inspection.
- **Data Warehouse Viewer**: High-density tabular dataset explorer supporting schema validity filtering, record anomaly inspection, and one-click CSV/JSON exports.
- **Automation Fleet Control**: Monitor recurring background pipelines, inspect execution success rates, manage schedule states, and trigger ad-hoc runs.

---

## Prerequisites

- **Node.js**: v20.x, v22.x, or v24.x (LTS recommended)
- **Package Manager**: `pnpm` (v9 or later)
- **Orbit Core Daemon**: Backend server running on `http://localhost:8000`

---

## Getting Started

### 1. Environment Configuration

Copy the example environment configuration:

```bash
cp .env.example .env
```

Default configuration:

```env
PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 2. Install Dependencies

```bash
pnpm install
```

### 3. Start Development Server

```bash
pnpm dev
```

The application will launch at `http://localhost:5173`. API calls to `/api/v1` are proxied to the configured Orbit Core backend.

---

## Production Build & Quality Checks

### 1. Type Checking

```bash
pnpm check
```

### 2. Build for Production

```bash
pnpm build
```

### 3. Preview Production Build

```bash
pnpm preview
```

---

## Project Structure

```text
app/
├── src/
│   ├── app.css              # Global tokens, Tailwind v4 theme, and glass styles
│   ├── app.html             # Root HTML template and web font imports
│   ├── lib/
│   │   ├── api/             # Typed API client and TypeScript interface definitions
│   │   ├── components/      # UI primitives, Goal Studio, Lineage DAG, and Data Table
│   │   │   ├── automations/ # Fleet management and run cards
│   │   │   ├── dashboard/   # Operator cards and summary metrics
│   │   │   ├── goals/       # Command bar and execution plan preview studio
│   │   │   ├── layout/      # Sidebar, top navigation, and daemon alert banners
│   │   │   ├── runs/        # Lineage DAG graph and stage drawer
│   │   │   └── ui/          # Buttons, Badges, Tabs, and Orbit Mark
│   │   └── state/           # Svelte 5 reactive stores and telemetry state
│   └── routes/              # SvelteKit file-based routes
│       ├── +layout.svelte   # Application shell and responsive sidebar
│       ├── +page.svelte     # Operator workspace and mission command bar
│       ├── automations/     # Fleet management and historical execution metrics
│       ├── runs/            # Real-time lineage DAG and telemetry inspection
│       └── data/            # High-density data warehouse viewer
├── static/                  # Static assets, SVG marks, and web manifest
├── svelte.config.js         # SvelteKit adapter configuration
└── vite.config.ts           # Vite build pipeline and proxy settings
```
