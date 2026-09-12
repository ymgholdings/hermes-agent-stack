# Netcup RS 2000 G12 — Hermes WebUI, LiteLLM & Agentic OS Development Stack

This document contains automated instructions for Claude Code CLI to configure your Netcup server with LiteLLM, Hermes WebUI, Tailscale VDN, and full agent execution runtimes aligned with the Delegate Setup Skill specification.

## Phase 1: OS Hardening & Prerequisites
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl wget git build-essential pkg-config libssl-dev unzip htop ufw python3 python3-pip python3-venv sqlite3
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
echo "y" | sudo ufw enable
```

## Phase 2: Tailscale VDN Setup
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo ufw allow in on tailscale0
echo "Run 'sudo tailscale up' to connect to your Tailnet."
```

## Phase 3: Runtime Environments & Databases
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh && rm get-docker.sh
sudo usermod -aG docker $USER

curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pnpm
sudo npx -y playwright install-deps
```

## Phase 4: LiteLLM & Hermes WebUI Deployment
```bash
sudo mkdir -p /opt/hermes-stack
sudo chown -R $USER:$USER /opt/hermes-stack
cd /opt/hermes-stack

cat << 'CONFIG' > litellm_config.yaml
model_list:
  - model_name: claude-3-5-sonnet
    litellm_params:
      model: openrouter/anthropic/claude-3.5-sonnet
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: gpt-4o
    litellm_params:
      model: openrouter/openai/gpt-4o
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: poolside-laguna-s
    litellm_params:
      model: openrouter/poolside/laguna-s-2.1:free
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: poolside-laguna-xs
    litellm_params:
      model: openrouter/poolside/laguna-xs-2.1:free
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: nemotron-4-340b-free
    litellm_params:
      model: openrouter/nvidia/nemotron-4-340b-instruct:free
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: nemotron-3-ultra-free
    litellm_params:
      model: openrouter/nvidia/nemotron-3-ultra:free
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: cohere-north-mini-free
    litellm_params:
      model: openrouter/cohere/north-mini-code:free
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: gemma-2-9b-free
    litellm_params:
      model: openrouter/google/gemma-2-9b-it:free
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: gemma-4-31b-free
    litellm_params:
      model: openrouter/google/gemma-4-31b:free
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: openrouter-free
    litellm_params:
      model: openrouter/openrouter/free
      api_key: os.environ/OPENROUTER_API_KEY

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  drop_params: true
CONFIG

cat << 'ENVFILE' > .env
OPENROUTER_API_KEY=sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE
LITELLM_MASTER_KEY=sk-litellm-netcup-master-key-12345
ENVFILE

cat << 'COMPOSE' > docker-compose.yml
version: '3.8'
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-v1.60.0
    container_name: litellm-proxy
    restart: unless-stopped
    ports: ["127.0.0.1:4000:4000"]
    env_file: [.env]
    volumes: [./litellm_config.yaml:/app/config.yaml]
    command: ["--config", "/app/config.yaml", "--port", "4000"]
  hermes-webui:
    image: ghcr.io/nesquena/hermes-webui:latest
    container_name: hermes-webui
    restart: unless-stopped
    ports: ["127.0.0.1:8787:8787"]
    environment:
      - OPENAI_API_BASE=http://litellm:4000/v1
      - OPENAI_API_KEY=sk-litellm-netcup-master-key-12345
      - DEFAULT_MODEL=claude-3-5-sonnet
    depends_on: [litellm]
  postgres:
    image: postgres:16-alpine
    container_name: agentic-os-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: agentic_os
      POSTGRES_USER: hermes
      POSTGRES_PASSWORD: agentic_os_password_99
    ports: ["127.0.0.1:5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
  redis:
    image: redis:7-alpine
    container_name: agentic-os-redis
    restart: unless-stopped
    ports: ["127.0.0.1:6379:6379"]
volumes:
  postgres_data:
COMPOSE

docker compose up -d
```

## Phase 5: Claude Code CLI Environment Configuration
```bash
sudo npm install -g @anthropic-ai/claude-code
cat << 'BASHRC' >> ~/.bashrc
export ANTHROPIC_BASE_URL="http://127.0.0.1:4000"
export ANTHROPIC_AUTH_TOKEN="sk-litellm-netcup-master-key-12345"
export ANTHROPIC_MODEL="claude-3-5-sonnet"
export ANTHROPIC_SMALL_FAST_MODEL="poolside-laguna-s"
BASHRC
```
