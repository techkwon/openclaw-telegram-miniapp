# End-to-End Example

This is a concrete deployment flow for a self-hosted installation.

## Example inputs
- repo path: `$HOME/openclaw-telegram-miniapp`
- bridge local URL: `http://127.0.0.1:8765`
- public origin: `https://miniapp.example.com`
- gateway URL: `http://127.0.0.1:18789`

## Example flow

```bash
git clone https://github.com/techkwon/openclaw-telegram-miniapp.git "$HOME/openclaw-telegram-miniapp"
cd "$HOME/openclaw-telegram-miniapp"

./scripts/install.sh \
  --miniapp-public-origin "https://miniapp.example.com" \
  --telegram-bot-token "$TELEGRAM_BOT_TOKEN" \
  --telegram-owner-id "$TELEGRAM_OWNER_ID" \
  --openclaw-base-url "$OPENCLAW_BASE_URL" \
  --openclaw-gateway-token "$OPENCLAW_GATEWAY_TOKEN"

./.venv/bin/python ./scripts/verify_deployment.py --env-file .generated/miniapp.env
```

## Expected results
- generated env file exists at `.generated/miniapp.env`
- generated runner exists at `.generated/run_bridge.sh`
- local `/health` succeeds
- public `/health` succeeds if public origin is configured
- Telegram Menu Button URL points to the same public origin
