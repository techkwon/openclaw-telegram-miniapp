# Agent Install Guide

This document is for OpenClaw agents that need to install or update `techkwon/openclaw-telegram-miniapp` directly from GitHub.

Goal:
- clone the repository
- configure the required environment
- start the local bridge service
- verify the deployment without guessing local conventions

## 1. Assumptions

Expected environment:
- OpenClaw Gateway is already installed and running
- `gateway.http.endpoints.chatCompletions.enabled=true`
- Git is available
- Python 3 is available
- Telegram bot token and owner user id are known
- A fixed HTTPS public origin is available if Telegram Mini App will be exposed publicly

## 2. Required inputs

The installing agent should gather or confirm these values before editing service files:

- `REPO_DIR` example: `$HOME/openclaw-telegram-miniapp`
- `OPENCLAW_BASE_URL` example: `http://127.0.0.1:18789`
- `MINIAPP_PUBLIC_ORIGIN` example: `https://miniapp.example.com`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_OWNER_ID` or `TELEGRAM_OWNER_IDS`
- `OPENCLAW_GATEWAY_TOKEN` or `OPENCLAW_GATEWAY_PASSWORD`
- optional `MINIAPP_SHARED_TOKEN`

## 3. Clone or update from GitHub

Fresh install:

```bash
git clone https://github.com/techkwon/openclaw-telegram-miniapp.git "$HOME/openclaw-telegram-miniapp"
cd "$HOME/openclaw-telegram-miniapp"
```

Update existing install:

```bash
cd "$HOME/openclaw-telegram-miniapp"
git pull --ff-only origin main
```

## 3-1. Automated install path

This repository now includes:

- `requirements.txt`
- `scripts/install.sh`
- `scripts/verify_deployment.py`
- `scripts/check_repo.sh`
- `scripts/smoke_install.sh`
- `scripts/runtime_smoke.sh`
- `docs/START_HERE.md`

Recommended agent flow:

```bash
cd "$HOME/openclaw-telegram-miniapp"
./scripts/install.sh \
  --miniapp-public-origin "https://miniapp.example.com" \
  --telegram-bot-token "$TELEGRAM_BOT_TOKEN" \
  --telegram-owner-id "$TELEGRAM_OWNER_ID" \
  --openclaw-base-url "$OPENCLAW_BASE_URL" \
  --openclaw-gateway-token "$OPENCLAW_GATEWAY_TOKEN"

./.venv/bin/python ./scripts/verify_deployment.py --env-file .generated/miniapp.env
```

The install script:
- creates `.venv`
- installs Python dependencies
- writes `.generated/miniapp.env`
- writes a generated runner script
- can install a launchd or systemd user service

Extra verification helpers:
- `scripts/check_repo.sh` validates repository-level checks
- `scripts/smoke_install.sh` simulates a fresh unattended install in a temporary directory
- `scripts/runtime_smoke.sh` starts a mock gateway and verifies the bridge can actually boot and answer local requests

## 4. Environment baseline

Start from `.env.example` and translate the values into the target service manager or shell environment.

Important variables:

```bash
MINIAPP_HOST=127.0.0.1
MINIAPP_PORT=8765
OPENCLAW_BASE_URL=http://127.0.0.1:18789
MINIAPP_PUBLIC_ORIGIN=https://miniapp.example.com
TELEGRAM_BOT_TOKEN=...
TELEGRAM_OWNER_ID=...
OPENCLAW_GATEWAY_TOKEN=...
MINIAPP_BROWSER_SESSION_TTL_SECONDS=1800
MINIAPP_RATE_LIMIT_WINDOW_SECONDS=60
MINIAPP_RATE_LIMIT_MAX_REQUESTS=180
MINIAPP_RATE_LIMIT_ACTION_MAX_REQUESTS=12
MINIAPP_AUTH_DEBUG=false
```

## 5. Service setup strategy

Choose one service strategy and keep it explicit.

### macOS launchd

Use either:
- generated install via `scripts/install.sh --service launchd`
- or manual templates `launchd/ai.openclaw.miniapp-bridge.plist` and `bridge/run_bridge.sh`

### Linux systemd

Use either:
- generated install via `scripts/install.sh --service systemd-user`
- or manual template `systemd/openclaw-miniapp-bridge.service`

## 6. Minimal verification steps

After install or update, the agent should verify in this order.

### local bridge health

```bash
curl http://127.0.0.1:8765/health
```

Expected: HTTP 200

### local docs or index

```bash
curl -I http://127.0.0.1:8765/
```

Expected: HTTP 200

### public health, if public origin is configured

```bash
curl https://miniapp.example.com/health
```

Expected: HTTP 200

### Mini App auth path

The agent should confirm:
- Telegram menu button URL matches `MINIAPP_PUBLIC_ORIGIN`
- Telegram owner id is correct
- browser fallback works only as a backup path, not the primary path

## 7. Fail-fast expectations

The bridge now exits early for obvious bad deployment states, including:
- invalid `OPENCLAW_BASE_URL`
- missing Telegram owner id configuration
- missing Telegram bot token configuration
- invalid `MINIAPP_PUBLIC_ORIGIN`

If the process exits immediately, inspect stderr or bridge logs first.

## 8. Agent checklist

An installing agent should be able to answer all of these with a concrete value before declaring success.

- Where is the repo cloned?
- Which service manager is used?
- What is the exact local bridge URL?
- What is the exact public origin?
- Where does the bridge read secrets from?
- Which Telegram user id is allowed?
- Is chat completions enabled on the OpenClaw Gateway?
- Did `/health` pass locally?
- Did `/health` pass publicly?

## 9. Do not assume

Agents should not silently assume:
- the repo lives under `/Users/techkwon/...`
- launchd is always the target
- `SECRETS_FILE` exists or matches this workspace
- the public hostname is already wired to Cloudflare
- Telegram Menu Button is already updated

If any of those are unknown, the agent should stop and surface the missing value clearly.
