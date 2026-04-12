# OpenClaw porting status

## Goal
Port the Hermes Telegram Mini App UI to OpenClaw while keeping the original MIT license obligations intact.

## Done in this initial fork
- Fork created under `techkwon/openclaw-telegram-miniapp`
- Upstream remote preserved for sync and attribution
- README rewritten to describe the fork honestly
- UI title/text changed from Hermes to OpenClaw in the main app shell
- chat model target switched to `openclaw/default`
- OpenClaw session/message headers wired in the chat client
- cron tab explicitly marked as needing an adapter instead of silently pretending compatibility

## Known gaps
- `/api/jobs` style cron endpoints are Hermes-specific in this project
- `/api/model-info` and `/api/session-usage` equivalents are not yet mapped to OpenClaw
- Telegram Mini App server-side auth/validation path still needs an OpenClaw-side implementation decision
- docs landing page and service templates still contain Hermes-specific content

## Recommended next implementation step
Build a tiny OpenClaw-side bridge with:
- `GET /api/model-info`
- `GET /api/session-usage`
- `GET/POST/PATCH/DELETE /api/jobs`
- `POST /api/command`

That bridge can proxy to OpenClaw HTTP and/or Control UI RPC surfaces while keeping the mini app mostly unchanged.
