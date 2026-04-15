# Release Notes Draft

## OpenClaw Telegram Mini App deployment readiness update

This release significantly improves deployment readiness for the OpenClaw Telegram Mini App.

### Highlights
- Added short-lived browser session tokens for fallback browser auth
- Added browser session refresh and revoke flows
- Reduced shared token exposure in browser fallback mode
- Hardened refresh flow with race mitigation and retry handling
- Added startup config validation for deployment safety
- Added structured JSON request logging for operations
- Expanded README and `.env.example` with production guidance

### Why it matters
This moves the project beyond a working fork and much closer to a deployment-ready self-hosted companion for OpenClaw.

It is especially useful for operators who want:
- safer browser fallback auth
- clearer deployment validation
- better troubleshooting signals in production
- more explicit self-hosted setup guidance
