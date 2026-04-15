#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="8876"
GATEWAY_PORT="18889"
MOCK_PID=""
BRIDGE_PID=""
cleanup() {
  [[ -n "$BRIDGE_PID" ]] && kill "$BRIDGE_PID" >/dev/null 2>&1 || true
  [[ -n "$MOCK_PID" ]] && kill "$MOCK_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cd "$REPO_DIR"
python3 scripts/mock_gateway.py "$GATEWAY_PORT" &
MOCK_PID=$!
sleep 1

MINIAPP_HOST=127.0.0.1 \
MINIAPP_PORT="$PORT" \
OPENCLAW_BASE_URL="http://127.0.0.1:${GATEWAY_PORT}" \
TELEGRAM_BOT_TOKEN="dummy-bot-token" \
TELEGRAM_OWNER_ID="123456789" \
OPENCLAW_GATEWAY_TOKEN="dummy-gateway-token" \
MINIAPP_AUTH_DEBUG=false \
python3 bridge/openclaw_miniapp_bridge.py >/tmp/openclaw-miniapp-runtime-smoke.out 2>/tmp/openclaw-miniapp-runtime-smoke.err &
BRIDGE_PID=$!

for _ in {1..20}; do
  if curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null

echo "RUNTIME_SMOKE_OK"
