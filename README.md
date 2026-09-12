# Hermes Agent Stack & Deployment Instructions

This repository contains the setup instructions, routing matrix, and deployable stack config for the Hermes multi-agent development environment.

## File Map

- `setup_instructions.md`: Narrative, phase-by-phase Netcup RS 2000 G12 server setup guide (Claude Code CLI, LiteLLM Proxy, Hermes WebUI, database dependencies).
- `hermes_coding_skills_matrix.md`: System prompt skills matrix governing sub-agent model routing and execution rules.
- `netcup-server/`: The actual deployable files referenced above:
  - `deploy.sh`: Runnable script for Phases 1, 2, 3, and 5 (OS hardening, Tailscale, Docker/Node/Playwright, Claude Code CLI env).
  - `docker-compose.yml`: LiteLLM proxy, Hermes WebUI, Postgres, and Redis services.
  - `litellm_config.yaml`: Model routing table LiteLLM uses to reach OpenRouter endpoints.
  - `.env.example`: Copy to `.env` and fill in real secrets before running `docker compose up -d`.

## Quick start on the server

```bash
git clone https://github.com/ymgholdings/hermes-agent-stack.git
cd hermes-agent-stack/netcup-server
cp .env.example .env   # edit with real OPENROUTER_API_KEY, LITELLM_MASTER_KEY, POSTGRES_PASSWORD
bash deploy.sh
```
