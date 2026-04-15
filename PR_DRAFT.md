# PR Draft

## Title
Improve deployment readiness and browser session security for OpenClaw Telegram Mini App

## Summary
This PR hardens the OpenClaw Telegram Mini App for real self-hosted deployment use.

It focuses on two areas:

1. Browser fallback auth security
2. Deployment readiness and operational clarity

## What changed

### Browser session security
- Added short-lived browser session tokens issued by the bridge
- Added `/api/auth/session`, `/api/auth/refresh`, and `/api/auth/revoke`
- Added automatic browser session refresh before expiry
- Added browser-side logout flow that revokes the active session token
- Reduced long-lived shared token exposure in fallback browser mode

### Reliability hardening
- Added server-side refresh cache/lock to reduce refresh race issues
- Added client-side in-flight refresh dedupe
- Added retry handling for transient refresh failures
- Unified browser token persistence flow to reduce partial storage failure cases

### Deployment readiness
- Added startup config validation for key deployment settings
- Added structured JSON request logging with request ID, status, duration, and auth kind
- Kept sensitive auth values out of logs
- Expanded `.env.example`
- Added production checklist and security notes to README

## Why this matters
- Makes the browser fallback path safer for self-hosted deployments
- Improves failure handling during session refresh
- Helps operators detect bad config earlier with fail-fast startup checks
- Makes production troubleshooting easier with structured request logs
- Raises the repo from a working fork to something much closer to deployment-ready

## Validation
- `python3 -m py_compile bridge/openclaw_miniapp_bridge.py`
- JS script parse check for `index.html`
- Manual diff review of auth/session flow and deployment docs

## Notes
- This is still optimized for personal or small self-hosted deployments, not a large multi-tenant service
- The remaining polish area is mostly documentation split and deeper operational guides, not core auth correctness

## Suggested reviewer focus
- Browser fallback auth lifecycle
- Refresh/revoke edge cases
- Startup validation scope
- Log safety and production usefulness
