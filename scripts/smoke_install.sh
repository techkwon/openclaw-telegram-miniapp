#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

TARGET_DIR="$TMP_DIR/openclaw-telegram-miniapp"
git clone "$REPO_DIR" "$TARGET_DIR" >/dev/null 2>&1
cd "$TARGET_DIR"

chmod +x scripts/install.sh scripts/verify_deployment.py scripts/check_repo.sh
./scripts/install.sh \
  --service none \
  --no-start \
  --miniapp-public-origin "https://miniapp.example.com" \
  --telegram-bot-token "dummy-bot-token" \
  --telegram-owner-id "123456789" \
  --openclaw-base-url "http://127.0.0.1:18789" \
  --openclaw-gateway-token "dummy-gateway-token"

test -f .generated/miniapp.env
test -x .generated/run_bridge.sh
test -x .venv/bin/python
./scripts/check_repo.sh >/dev/null

echo "SMOKE_INSTALL_OK"
