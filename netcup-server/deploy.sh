#!/usr/bin/env bash
# Netcup RS 2000 G12 -- Hermes WebUI, LiteLLM & Agentic OS Development Stack
# Run this on the target server as: bash deploy.sh
set -euo pipefail

echo "== Phase 1: OS hardening & prerequisites =="
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl wget git build-essential pkg-config libssl-dev unzip htop ufw python3 python3-pip python3-venv sqlite3
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
echo "y" | sudo ufw enable

echo "== Phase 2: Tailscale VDN setup =="
curl -fsSL https://tailscale.com/install.sh | sh
sudo ufw allow in on tailscale0
echo "ACTION REQUIRED: run 'sudo tailscale up' to connect this server to your Tailnet."

echo "== Phase 3: Runtime environments & databases =="
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh && rm get-docker.sh
sudo usermod -aG docker "$USER"
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pnpm
sudo npx -y playwright install-deps

echo "== Phase 4: LiteLLM + Hermes WebUI stack =="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example -- edit it with real secrets before continuing."
  exit 1
fi
docker compose up -d

echo "== Phase 5: Claude Code CLI environment =="
sudo npm install -g @anthropic-ai/claude-code
cat << 'BASHRC' >> ~/.bashrc
export ANTHROPIC_BASE_URL="http://127.0.0.1:4000"
export ANTHROPIC_AUTH_TOKEN="$(grep LITELLM_MASTER_KEY .env | cut -d= -f2)"
export ANTHROPIC_MODEL="claude-3-5-sonnet"
export ANTHROPIC_SMALL_FAST_MODEL="poolside-laguna-s"
BASHRC

echo "Done. Source ~/.bashrc (or start a new shell) then run: claude --version"
