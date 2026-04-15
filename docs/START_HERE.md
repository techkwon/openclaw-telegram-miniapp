# Start Here

If you just opened this repository and want the fastest correct path, use this page.

## Choose your path

### I am an OpenClaw agent
1. Read [`docs/AGENT_INSTALL.md`](AGENT_INSTALL.md)
2. Read [`docs/GITHUB_DEPLOYMENT.md`](GITHUB_DEPLOYMENT.md)
3. Run `scripts/install.sh`
4. Run `scripts/verify_deployment.py`

### I am deploying it myself
1. Read [`README.md`](../README.md)
2. Read [`OPERATIONS_CHECKLIST.md`](../OPERATIONS_CHECKLIST.md)
3. Use the service template for your OS

### I want to understand the architecture
- Read [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)

### I want an end-to-end example
- Read [`docs/E2E_EXAMPLE.md`](E2E_EXAMPLE.md)

## Minimum success criteria

Do not call the deploy complete until all of these are true:
- local `/health` works
- public `/health` works if public origin is configured
- Telegram Mini App URL matches the configured public origin
- secrets are not committed to GitHub
