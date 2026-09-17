# Agentic OS v1 - Installation & Usage Guide

## Quick Start

### 1. Prerequisites Check

Ensure the netcup-server stack is running:
```bash
cd /root/hermes-agent-stack/netcup-server
docker compose ps
# Should show: litellm-proxy, hermes-webui, agentic-os-db, agentic-os-redis all running
```

### 2. Install Agentic OS CLI

```bash
cd /root/hermes-agent-stack/agentic-os
pipx install -e .
export PATH="$HOME/.local/bin:$PATH"  # Add to ~/.bashrc to persist
```

### 3. Configure Environment

The `.env` file should already be configured with correct values from netcup-server:
```bash
cat .env
# Verify LITELLM_MASTER_KEY and DATABASE_URL match netcup-server/.env
```

### 4. Test Connections

```bash
agentic-os test-connections
```

Expected output:
```
✓ All connections successful!
```

### 5. Submit Your First Task

```bash
agentic-os submit "write a fibonacci function with unit tests"
```

You'll see progress through all 4 stages:
1. **Decomposing** (Orchestrator - Claude Sonnet 4.5)
2. **Implementing** (Core Implementer - Poolside Laguna-S, free tier)
3. **Debugging** (Debugger - Nemotron 4-340B, free tier)
4. **Testing** (Sandboxed Docker container)

Final code will be displayed in the terminal and saved to the database.

### 6. View Task History

```bash
agentic-os list
agentic-os list --limit 20
agentic-os show 1  # Show detailed output for task #1
```

## Architecture

```
┌─────────────────┐
│  CLI (Rich UI)  │
└────────┬────────┘
         │
    ┌────▼──────────────────────────────────────┐
    │      Orchestrator (Claude Sonnet 4.5)     │
    │  - Task decomposition                      │
    │  - Final merge approval                    │
    └────┬──────────────────────────────────────┘
         │
         ├──► Implementer (Poolside Laguna-S, free)
         │    Generates code + tests
         │
         ├──► Debugger (Nemotron 4-340B, free)
         │    Reviews for bugs, security issues
         │
         └──► Executor (Docker sandbox)
              Runs tests, validates output
```

## Cost Breakdown

- **Orchestrator**: ~$0.003/1K tokens (Claude Sonnet 4.5)
- **Implementer**: FREE (OpenRouter)
- **Debugger**: FREE (OpenRouter)

Typical task: **< $0.10** total cost

## Security

- Generated code runs in throwaway `python:3.11-slim` Docker containers
- 30-second timeout per test run
- No network access during execution (`--network=none`)
- Container auto-removed after execution (`--rm`)
- Memory/CPU limits enforced

## Troubleshooting

### Database connection failed
```bash
# Check Postgres is running
docker ps | grep agentic-os-db

# Check password matches
grep POSTGRES_PASSWORD netcup-server/.env
grep DATABASE_URL agentic-os/.env
```

### LiteLLM connection failed
```bash
# Check LiteLLM proxy is running
curl http://127.0.0.1:4000/

# Check API key matches
grep LITELLM_MASTER_KEY netcup-server/.env
grep LITELLM_MASTER_KEY agentic-os/.env
```

### Docker not available
```bash
docker info
# If fails, start Docker daemon
```

### Rate limit errors (429)
The system automatically handles this:
1. Waits 3 seconds and retries
2. Falls back to alternate models (per skills matrix)
3. Uses `openrouter/openrouter/free` as last resort

## Development

### Running from source (without install)
```bash
cd /root/hermes-agent-stack/agentic-os
python -m agentic_os.cli submit "your task here"
```

### Updating after code changes
```bash
pipx reinstall agentic-os
```

### Database schema
```bash
# View schema
docker exec agentic-os-db psql -U hermes -d agentic_os -c "\d tasks"

# Manual queries
docker exec agentic-os-db psql -U hermes -d agentic_os -c "SELECT id, status, spec FROM tasks;"
```

## What's Next (v2 Ideas)

- [ ] Async orchestration for parallel sub-tasks
- [ ] Web UI for task submission/monitoring
- [ ] Multi-task queue processing
- [ ] Streaming progress updates
- [ ] Code artifact storage (S3/filesystem)
- [ ] GitHub integration (PR creation from tasks)
- [ ] More agent roles (Context Cruncher for docs)
- [ ] Custom task types beyond "function + tests"
