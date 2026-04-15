#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

python3 -m py_compile bridge/openclaw_miniapp_bridge.py scripts/verify_deployment.py
bash -n scripts/install.sh
python3 scripts/verify_deployment.py --help >/dev/null

echo "REPO_CHECK_OK"
