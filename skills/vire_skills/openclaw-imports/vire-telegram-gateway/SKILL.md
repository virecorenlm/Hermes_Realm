---
name: vire-telegram-gateway
description: "Use when setting up, verifying, or troubleshooting remote messaging access to Vire via the Hermes Telegram gateway: token/home-channel checks, gateway logs, /sethome flow, and polling-conflict pitfalls."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [telegram, hermes, gateway, remote-access, messaging]
    related_skills: [vire]
---

# Vire — Remote Messaging Access: Telegram Gateway

Use this when the operator wants Vire reachable while he is away from the terminal. Hermes Telegram is the default remote chat path.

## Setup / Verification Flow

1. Consult the `hermes-agent` skill for current gateway commands before changing Hermes config.
2. Verify service state with `hermes gateway status`.
3. Confirm config and secret locations with `hermes config path` and `hermes config env-path`.
4. Check Telegram readiness without leaking secrets:
   - `TELEGRAM_BOT_TOKEN` exists in `~/.hermes/.env`
   - `TELEGRAM_ALLOWED_USERS` is set if access should be restricted
   - `TELEGRAM_HOME_CHANNEL` is set after `/sethome`, or the gateway has a home channel recorded
5. Validate the bot token with Telegram `getMe` only if necessary; report the bot username and status, never the token.
6. Check `~/.hermes/logs/gateway.log` for `Connected to Telegram (polling mode)`.
7. If connected but outbound messages have no destination, tell the operator to open the bot in Telegram and send `/start`, then `/sethome`.
8. After `/sethome`, send a harmless test message and verify delivery before claiming the setup is done.

Detailed notes: `references/telegram-gateway-remote-access.md`.

## Pitfalls

- A running gateway plus valid bot token does not guarantee outbound delivery; bare Telegram sends need a home chat.
- Polling conflict warnings can be transient after restarts. If the log later shows polling resumed or Telegram connected, do not treat the conflict as the active blocker.
- Keep tokens, chat IDs, and user IDs out of normal replies unless the operator explicitly asks for the raw values.
