# OpenClaw mini app bridge

Run locally:

```bash
MINIAPP_PORT=8765 \
OPENCLAW_BASE_URL=http://127.0.0.1:18789 \
MINIAPP_SHARED_TOKEN=your-miniapp-token \
OPENCLAW_GATEWAY_TOKEN=your-gateway-token \
python3 bridge/openclaw_miniapp_bridge.py
```

Then open:
- `http://127.0.0.1:8765/`
- docs: `http://127.0.0.1:8765/docs/`

Current bridge scope:
- static mini app serving
- `/v1/chat/completions` proxy to OpenClaw gateway
- `/api/model-info`
- `/api/session-usage`
- `/api/jobs` CRUD via `openclaw cron`
- `/api/command` lightweight compatibility layer

Current limitation:
- Telegram Mini App initData verification is not implemented yet in this bridge
- bearer/shared-token mode is the current auth path
- OpenClaw chat proxying needs `gateway.http.endpoints.chatCompletions.enabled=true`
