#!/bin/zsh
set -euo pipefail

REPO_DIR="${OPENCLAW_MINIAPP_REPO_DIR:-$HOME/.openclaw/workspace/openclaw-telegram-miniapp}"
SECRETS_FILE="${OPENCLAW_SECRETS_FILE:-$HOME/.openclaw/secrets.store.json}"
MINIAPP_HOST="${MINIAPP_HOST:-127.0.0.1}"
MINIAPP_PORT="${MINIAPP_PORT:-8765}"
OPENCLAW_BASE_URL="${OPENCLAW_BASE_URL:-http://127.0.0.1:18789}"
MINIAPP_SHARED_TOKEN="${MINIAPP_SHARED_TOKEN:-dev-miniapp-token}"

GATEWAY_TOKEN="$(python3 - <<'PY'
import json
import os
from pathlib import Path
p = Path(os.environ['SECRETS_FILE'])
obj = json.loads(p.read_text())
print(obj['gateway']['token'])
PY
)"

cd "$REPO_DIR"
export MINIAPP_HOST MINIAPP_PORT OPENCLAW_BASE_URL MINIAPP_SHARED_TOKEN OPENCLAW_GATEWAY_TOKEN="$GATEWAY_TOKEN"
exec python3 "$REPO_DIR/bridge/openclaw_miniapp_bridge.py"
