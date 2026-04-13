# OpenClaw mini app bridge

로컬 실행 예시:

```bash
MINIAPP_PORT=8765 \
OPENCLAW_BASE_URL=http://127.0.0.1:18789 \
TELEGRAM_BOT_TOKEN=your-telegram-bot-token \
OPENCLAW_GATEWAY_TOKEN=your-gateway-token \
python3 bridge/openclaw_miniapp_bridge.py
```

열기:
- `http://127.0.0.1:8765/`
- docs: `http://127.0.0.1:8765/docs/`

현재 bridge 범위:
- 정적 mini app 서빙
- `/v1/chat/completions` 를 OpenClaw gateway로 프록시
- `/api/model-info`
- `/api/session-usage`
- `/api/jobs` CRUD via `openclaw cron`
- `/api/command` 호환 레이어

현재 인증 방식:
- Telegram Mini App 내부에서는 `X-Telegram-Init-Data`를 서버에서 검증
- 브라우저 테스트용으로는 Bearer/shared-token fallback 지원
- 여러 Telegram bot token을 함께 허용 가능

운영 권장 설정:
- `MINIAPP_PUBLIC_ORIGIN=https://your-domain.example`
- `TELEGRAM_OWNER_ID=<your numeric telegram user id>` 또는 `TELEGRAM_OWNER_IDS=...`
- `MINIAPP_AUTH_DEBUG=true` 는 문제 추적 시에만 임시 사용
- 현재 로컬 launchd 예시는 owner 제한을 적용해 둘 수 있음

주의:
- OpenClaw chat 프록시는 `gateway.http.endpoints.chatCompletions.enabled=true` 가 필요함
