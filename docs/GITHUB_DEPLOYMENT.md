# GitHub-Only Deployment Guide

This guide explains how to deploy `techkwon/openclaw-telegram-miniapp` using the GitHub repository as the source of truth.

The intended model is:
- OpenClaw agent reads this repository
- clones or updates from GitHub
- applies environment-specific values locally
- starts or reloads the bridge service
- verifies health endpoints
- runs the same repository checks locally and in CI

## Deployment model

Source of truth:
- GitHub repository contents
- committed docs, templates, and service examples

Local machine responsibilities:
- secrets
- exact hostname
- exact Telegram bot configuration
- service manager wiring

That means agents should install from GitHub, but should never commit machine-local secrets back into the repository.

## Recommended workflow

### Fresh deployment

```bash
git clone https://github.com/techkwon/openclaw-telegram-miniapp.git "$HOME/openclaw-telegram-miniapp"
cd "$HOME/openclaw-telegram-miniapp"
```

Then:
1. read `.env.example`
2. read `docs/AGENT_INSTALL.md`
3. run `scripts/install.sh` with machine-local values
4. verify with `scripts/verify_deployment.py`
5. only then declare success

### Update deployment

```bash
cd "$HOME/openclaw-telegram-miniapp"
git fetch origin
git checkout main
git pull --ff-only origin main
```

Then restart the bridge service and repeat health verification.

## What should stay in GitHub

Safe to keep in the repo:
- README
- docs
- service templates
- helper scripts
- non-secret defaults

Never commit:
- Telegram bot tokens
- gateway tokens
- password-mode shared secrets
- machine-local secret stores
- user-specific absolute secret file paths unless they are only examples

## Files agents should read first

1. `README.md`
2. `.env.example`
3. `requirements.txt`
4. `docs/AGENT_INSTALL.md`
5. `scripts/install.sh`
6. `scripts/verify_deployment.py`
7. `scripts/check_repo.sh`
8. `OPERATIONS_CHECKLIST.md`
9. `Dockerfile`
10. service template matching the host OS

## Automation files included in this repo

- `requirements.txt`
- `scripts/install.sh`
- `scripts/verify_deployment.py`
- `scripts/check_repo.sh`
- `scripts/smoke_install.sh`
- `.github/workflows/ci.yml`
- `Dockerfile`
- `docker-compose.yml`

## Container deployment example

Quick example:

```bash
docker compose up -d --build
```

Expected local endpoint:

```bash
curl http://127.0.0.1:8765/health
```

The compose file is an example and still expects machine-local secrets via environment variables.

## Service files included in this repo

### macOS
- `launchd/ai.openclaw.miniapp-bridge.plist`
- `bridge/run_bridge.sh`

### Linux
- `systemd/openclaw-miniapp-bridge.service`

These are templates, not universal drop-in files. Agents should patch values to match the actual host.

## Required verification after every deploy

```bash
curl http://127.0.0.1:8765/health
```

If public deployment is expected:

```bash
curl https://your-domain.example/health
```

Also verify:
- Mini App URL in Telegram matches the public origin
- OpenClaw Gateway chat endpoint is enabled
- bridge logs do not show startup validation failure

## Reproducibility note

CI now checks three layers:
- repository syntax and local checks
- unattended install smoke test via `scripts/smoke_install.sh`
- Docker image build

This does not replace a real production deploy, but it closes most of the earlier reproducibility gap.

## Suggested agent success criteria

An agent should only declare deployment complete when all are true:
- repository is present at the target path
- service file is installed and running
- local `/health` returns success
- public `/health` returns success when public origin is configured
- Telegram Mini App URL is confirmed
- secrets are stored outside GitHub

## Why this guide exists

The repo is now intended to be installable directly by OpenClaw agents.

That only works well when the repository tells the agent:
- what to read first
- what values must be supplied
- what is a template versus what is machine-local
- what verification is required before saying “done”
