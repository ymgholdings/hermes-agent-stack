# Agentic OS v1

Multi-agent coding orchestration system implementing the Karpathy validation loop (Implementer → Debugger/QA → Architect merge).

## Architecture

- **Orchestrator:** Claude Sonnet 4.5 (via LiteLLM) - task decomposition, merge approval
- **Core Implementer:** Poolside Laguna-S (OpenRouter free tier) - code generation
- **Debugger/QA:** Nvidia Nemotron 4-340B (OpenRouter free tier) - code review, bug detection
- **Executor:** Sandboxed Docker containers - test validation

## Setup

### 1. Prerequisites

- Docker installed and running
- PostgreSQL 16 (running via docker-compose in `netcup-server/`)
- Redis 7 (running via docker-compose in `netcup-server/`)
- LiteLLM proxy (running at http://127.0.0.1:4000)
- Python 3.11+

### 2. Create Database

```bash
docker exec -it agentic-os-db psql -U hermes -d postgres -c "CREATE DATABASE agentic_os;"
```

### 3. Initialize Schema

```bash
docker exec -i agentic-os-db psql -U hermes -d agentic_os < schema.sql
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (defaults match netcup-server setup)
```

### 5. Install Package

```bash
pip install -e .
```

## Usage

### Submit a coding task

```bash
agentic-os submit "write a fibonacci function with unit tests"
```

Output shows progress through all stages:
1. Decomposing task (Orchestrator)
2. Core implementation (Poolside Laguna-S)
3. Debugger review (Nemotron 4-340B)
4. Running tests (sandboxed Docker)
5. Final merge (Orchestrator)

### List task history

```bash
agentic-os list
```

## Cost Efficiency

- Orchestrator: ~$0.003/1K input tokens (Claude Sonnet 4.5)
- Implementer: FREE (Poolside Laguna-S via OpenRouter)
- Debugger: FREE (Nemotron 4-340B via OpenRouter)
- Typical task: <$0.10 total cost

## Security

- Generated code runs in throwaway Docker containers
- 30-second timeout per test run
- No network access during execution
- Container auto-removed after run
- No access to host filesystem beyond test directory

## Rate Limits

OpenRouter free-tier models limited to ~20 requests/minute. The system automatically:
1. Detects 429 errors
2. Waits 3 seconds and retries
3. Falls back to alternate models per routing matrix
4. Uses `openrouter/free` as last resort

## Architecture Details

See `DESIGN_V1.md` for complete design document including execution flow, Postgres schema, and Redis patterns.
