# OpenClaw Telegram Mini App

OpenClaw-focused fork of the original [clawvader-tech/hermes-telegram-miniapp](https://github.com/clawvader-tech/hermes-telegram-miniapp), kept under the original MIT license.

## Status

This repository is being ported for **OpenClaw**.

Current first-pass scope:
- keep the single-file Telegram Mini App UI
- route chat to OpenClaw `POST /v1/chat/completions`
- preserve Telegram WebApp shell and local session storage
- document missing pieces instead of pretending Hermes-only endpoints exist

## What works in this fork today

- OpenClaw branding and docs baseline
- chat requests target `model: "openclaw/default"`
- session header uses `x-openclaw-session-id`
- synthetic ingress channel header uses `x-openclaw-message-channel`
- Bearer-token style gateway auth remains supported for browser fallback

## What still needs OpenClaw-specific work

- cron tab currently needs an **OpenClaw adapter layer** or **Control UI RPC bridge**
- model/session usage/status cards need richer OpenClaw-native endpoints or WS integration
- Telegram Mini App auth should be matched to the chosen OpenClaw gateway exposure pattern
- deployment docs should be rewritten around OpenClaw gateway config, not Hermes service layout

## Development approach

We are keeping license obligations intact:
- retain upstream MIT `LICENSE`
- keep clear attribution to the original project
- document fork status honestly
- avoid claiming unsupported Hermes-only backend features work on OpenClaw

## Suggested next milestones

1. add an OpenClaw cron bridge
2. add status/model/session usage bridge
3. replace remaining Hermes strings in docs/demo assets
4. add Telegram deployment instructions for OpenClaw gateway + tunnel

## Upstream

- Original project: <https://github.com/clawvader-tech/hermes-telegram-miniapp>
- This fork: <https://github.com/techkwon/openclaw-telegram-miniapp>

## License

Original project and this fork are distributed under the MIT License. See [LICENSE](LICENSE).
