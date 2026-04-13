#!/bin/zsh
set -euo pipefail

REPO_DIR="${OPENCLAW_MINIAPP_REPO_DIR:-$HOME/.openclaw/workspace/openclaw-telegram-miniapp}"
SECRETS_FILE="${OPENCLAW_SECRETS_FILE:-$HOME/.openclaw/secrets.store.json}"
MINIAPP_HOST="${MINIAPP_HOST:-127.0.0.1}"
MINIAPP_PORT="${MINIAPP_PORT:-8765}"
OPENCLAW_BASE_URL="${OPENCLAW_BASE_URL:-http://127.0.0.1:18789}"
MINIAPP_SHARED_TOKEN="${MINIAPP_SHARED_TOKEN:-}"
TELEGRAM_ACCOUNT_NAME="${TELEGRAM_ACCOUNT_NAME:-default}"
MINIAPP_PUBLIC_ORIGIN="${MINIAPP_PUBLIC_ORIGIN:-}"
MINIAPP_INITDATA_MAX_AGE_SECONDS="${MINIAPP_INITDATA_MAX_AGE_SECONDS:-86400}"
MINIAPP_AUTH_DEBUG="${MINIAPP_AUTH_DEBUG:-}"
TELEGRAM_OWNER_ID="${TELEGRAM_OWNER_ID:-}"
TELEGRAM_OWNER_IDS="${TELEGRAM_OWNER_IDS:-}"

read_secret() {
  local key="$1"
  python3 - "$key" <<'PY'
import json
import os
import sys
from pathlib import Path
p = Path(os.environ['SECRETS_FILE'])
obj = json.loads(p.read_text())
key = sys.argv[1]
if key == 'gateway.token':
    print(obj['gateway']['token'])
elif key == 'telegram.botToken':
    account = os.environ.get('TELEGRAM_ACCOUNT_NAME', 'default')
    print(obj['channels']['telegram']['accounts'][account]['botToken'])
elif key == 'telegram.allBotTokens':
    accounts = obj.get('channels', {}).get('telegram', {}).get('accounts', {})
    for account in accounts.values():
        token = (account.get('botToken') or '').strip()
        if token:
            print(token)
else:
    raise SystemExit(f'unknown key: {key}')
PY
}

GATEWAY_TOKEN="$(read_secret gateway.token)"
TELEGRAM_BOT_TOKEN="$(read_secret telegram.botToken)"
TELEGRAM_BOT_TOKENS="$(read_secret telegram.allBotTokens)"

cd "$REPO_DIR"
export MINIAPP_HOST MINIAPP_PORT OPENCLAW_BASE_URL MINIAPP_PUBLIC_ORIGIN MINIAPP_INITDATA_MAX_AGE_SECONDS MINIAPP_AUTH_DEBUG
export TELEGRAM_ACCOUNT_NAME TELEGRAM_BOT_TOKEN TELEGRAM_BOT_TOKENS TELEGRAM_OWNER_ID TELEGRAM_OWNER_IDS OPENCLAW_GATEWAY_TOKEN="$GATEWAY_TOKEN"
if [[ -n "$MINIAPP_SHARED_TOKEN" ]]; then
  export MINIAPP_SHARED_TOKEN
fi
exec python3 "$REPO_DIR/bridge/openclaw_miniapp_bridge.py"
