#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_ENV_FILE="$REPO_DIR/.generated/miniapp.env"
DEFAULT_RUNNER="$REPO_DIR/.generated/run_bridge.sh"
SERVICE_MODE="auto"
START_SERVICE=1
ENV_FILE="$DEFAULT_ENV_FILE"
PYTHON_BIN="${PYTHON_BIN:-python3}"

MINIAPP_HOST="${MINIAPP_HOST:-127.0.0.1}"
MINIAPP_PORT="${MINIAPP_PORT:-8765}"
OPENCLAW_BASE_URL="${OPENCLAW_BASE_URL:-http://127.0.0.1:18789}"
MINIAPP_PUBLIC_ORIGIN="${MINIAPP_PUBLIC_ORIGIN:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_OWNER_ID="${TELEGRAM_OWNER_ID:-}"
TELEGRAM_OWNER_IDS="${TELEGRAM_OWNER_IDS:-}"
OPENCLAW_GATEWAY_TOKEN="${OPENCLAW_GATEWAY_TOKEN:-}"
OPENCLAW_GATEWAY_PASSWORD="${OPENCLAW_GATEWAY_PASSWORD:-}"
MINIAPP_SHARED_TOKEN="${MINIAPP_SHARED_TOKEN:-}"
MINIAPP_BROWSER_SESSION_TTL_SECONDS="${MINIAPP_BROWSER_SESSION_TTL_SECONDS:-1800}"
MINIAPP_RATE_LIMIT_WINDOW_SECONDS="${MINIAPP_RATE_LIMIT_WINDOW_SECONDS:-60}"
MINIAPP_RATE_LIMIT_MAX_REQUESTS="${MINIAPP_RATE_LIMIT_MAX_REQUESTS:-180}"
MINIAPP_RATE_LIMIT_ACTION_MAX_REQUESTS="${MINIAPP_RATE_LIMIT_ACTION_MAX_REQUESTS:-12}"
MINIAPP_AUTH_DEBUG="${MINIAPP_AUTH_DEBUG:-false}"

usage() {
  cat <<EOF
Usage: scripts/install.sh [options]

Options:
  --service <auto|launchd|systemd-user|none>
  --env-file <path>
  --no-start
  --miniapp-public-origin <url>
  --telegram-bot-token <token>
  --telegram-owner-id <id>
  --telegram-owner-ids <csv>
  --openclaw-base-url <url>
  --openclaw-gateway-token <token>
  --openclaw-gateway-password <password>
  --miniapp-shared-token <token>
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service) SERVICE_MODE="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --no-start) START_SERVICE=0; shift ;;
    --miniapp-public-origin) MINIAPP_PUBLIC_ORIGIN="$2"; shift 2 ;;
    --telegram-bot-token) TELEGRAM_BOT_TOKEN="$2"; shift 2 ;;
    --telegram-owner-id) TELEGRAM_OWNER_ID="$2"; shift 2 ;;
    --telegram-owner-ids) TELEGRAM_OWNER_IDS="$2"; shift 2 ;;
    --openclaw-base-url) OPENCLAW_BASE_URL="$2"; shift 2 ;;
    --openclaw-gateway-token) OPENCLAW_GATEWAY_TOKEN="$2"; shift 2 ;;
    --openclaw-gateway-password) OPENCLAW_GATEWAY_PASSWORD="$2"; shift 2 ;;
    --miniapp-shared-token) MINIAPP_SHARED_TOKEN="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

require_cmd "$PYTHON_BIN"
require_cmd git
mkdir -p "$REPO_DIR/.generated"

if [[ -z "$TELEGRAM_BOT_TOKEN" ]]; then
  echo "TELEGRAM_BOT_TOKEN is required" >&2
  exit 1
fi
if [[ -z "$TELEGRAM_OWNER_ID" && -z "$TELEGRAM_OWNER_IDS" ]]; then
  echo "TELEGRAM_OWNER_ID or TELEGRAM_OWNER_IDS is required" >&2
  exit 1
fi
if [[ -z "$OPENCLAW_GATEWAY_TOKEN" && -z "$OPENCLAW_GATEWAY_PASSWORD" ]]; then
  echo "OPENCLAW_GATEWAY_TOKEN or OPENCLAW_GATEWAY_PASSWORD is required" >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install --upgrade pip >/dev/null
"$REPO_DIR/.venv/bin/pip" install -r "$REPO_DIR/requirements.txt"

cat > "$ENV_FILE" <<EOF
MINIAPP_HOST=$MINIAPP_HOST
MINIAPP_PORT=$MINIAPP_PORT
OPENCLAW_BASE_URL=$OPENCLAW_BASE_URL
MINIAPP_PUBLIC_ORIGIN=$MINIAPP_PUBLIC_ORIGIN
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
TELEGRAM_OWNER_ID=$TELEGRAM_OWNER_ID
TELEGRAM_OWNER_IDS=$TELEGRAM_OWNER_IDS
OPENCLAW_GATEWAY_TOKEN=$OPENCLAW_GATEWAY_TOKEN
OPENCLAW_GATEWAY_PASSWORD=$OPENCLAW_GATEWAY_PASSWORD
MINIAPP_SHARED_TOKEN=$MINIAPP_SHARED_TOKEN
MINIAPP_BROWSER_SESSION_TTL_SECONDS=$MINIAPP_BROWSER_SESSION_TTL_SECONDS
MINIAPP_RATE_LIMIT_WINDOW_SECONDS=$MINIAPP_RATE_LIMIT_WINDOW_SECONDS
MINIAPP_RATE_LIMIT_MAX_REQUESTS=$MINIAPP_RATE_LIMIT_MAX_REQUESTS
MINIAPP_RATE_LIMIT_ACTION_MAX_REQUESTS=$MINIAPP_RATE_LIMIT_ACTION_MAX_REQUESTS
MINIAPP_AUTH_DEBUG=$MINIAPP_AUTH_DEBUG
EOF

cat > "$DEFAULT_RUNNER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
set -a
source "$ENV_FILE"
set +a
exec "$REPO_DIR/.venv/bin/python" "$REPO_DIR/bridge/openclaw_miniapp_bridge.py"
EOF
chmod +x "$DEFAULT_RUNNER"

if [[ "$SERVICE_MODE" == "auto" ]]; then
  case "$(uname -s)" in
    Darwin) SERVICE_MODE="launchd" ;;
    Linux) SERVICE_MODE="systemd-user" ;;
    *) SERVICE_MODE="none" ;;
  esac
fi

install_launchd() {
  local plist="$HOME/Library/LaunchAgents/ai.openclaw.miniapp-bridge.generated.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>ai.openclaw.miniapp-bridge.generated</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProgramArguments</key>
    <array>
      <string>$DEFAULT_RUNNER</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
    <key>StandardOutPath</key>
    <string>$HOME/.openclaw/logs/openclaw-miniapp-bridge.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.openclaw/logs/openclaw-miniapp-bridge.err.log</string>
  </dict>
</plist>
EOF
  mkdir -p "$HOME/.openclaw/logs"
  if [[ "$START_SERVICE" -eq 1 ]]; then
    launchctl bootout "gui/$(id -u)" "$plist" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    launchctl kickstart -k "gui/$(id -u)/ai.openclaw.miniapp-bridge.generated"
  fi
  echo "launchd plist: $plist"
}

install_systemd_user() {
  require_cmd systemctl
  local unit_dir="$HOME/.config/systemd/user"
  local unit="$unit_dir/openclaw-miniapp-bridge-generated.service"
  mkdir -p "$unit_dir" "$HOME/.openclaw/logs"
  cat > "$unit" <<EOF
[Unit]
Description=OpenClaw Telegram Mini App Bridge (generated)
After=network.target

[Service]
Type=simple
WorkingDirectory=$REPO_DIR
ExecStart=$DEFAULT_RUNNER
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
  if [[ "$START_SERVICE" -eq 1 ]]; then
    systemctl --user daemon-reload
    systemctl --user enable --now openclaw-miniapp-bridge-generated.service
  fi
  echo "systemd user unit: $unit"
}

case "$SERVICE_MODE" in
  launchd) install_launchd ;;
  systemd-user) install_systemd_user ;;
  none) echo "Service install skipped (--service none)" ;;
  *) echo "Unsupported service mode: $SERVICE_MODE" >&2; exit 1 ;;
esac

echo "Env file: $ENV_FILE"
echo "Runner: $DEFAULT_RUNNER"
echo "Next: $REPO_DIR/.venv/bin/python $REPO_DIR/scripts/verify_deployment.py --env-file $ENV_FILE"
