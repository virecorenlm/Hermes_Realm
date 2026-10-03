---
name: vire
description: "Index for optional Hermes Realm skills and their safety boundaries."
version: 2.0.0
author: Vire Shorette
license: MIT
---

# Hermes Realm skill index

Start with a single machine. Select a focused skill only when its integration is configured. The corresponding `vire-*` skills cover memory, voice, Gmail, Meta, TikTok, Shopify, n8n, content, and file organization. Several imported skills describe companion programs outside this repository; verify availability before following commands.

## Configuration

Use `HERMES_REALM_HOME` for Realm state and secrets. Its default is `${XDG_CONFIG_HOME:-$HOME/.config}/hermes-realm`. Use `OLLAMA_URL`, `QDRANT_URL`, `N8N_URL`, and `REDIS_URL` for optional services. Keep filled credential files under the private `secrets/` directory with restricted permissions. Upstream Hermes owns `~/.hermes`.

## Guardrails

- Read-only inspection and local draft creation are the starting scope.
- Confirm destructive actions, external-account changes, and spending.
- Restrict queue writers and keep shell and HTTP task types disabled until deliberately configured.
- Verify API responses before reporting success; never print secrets.
- Use [vire-autonomy-modes](../vire-autonomy-modes/SKILL.md) for the permission model.
