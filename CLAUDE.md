# Working on Hermes Realm

Hermes Realm is a public integration kit for upstream Hermes Agent. Treat the repository as reusable source and examples, with one-computer defaults and optional remote services. Do not add real hostnames, personal accounts, private memory exports, or credential files.

## Code map

- `scripts/realm_config.py` defines standalone-script service URLs and Realm application paths.
- `scripts/` contains optional voice, memory, task queue, vision, forecast, and Meta examples.
- `cron-pulses/` contains scheduled experiments; review write and external actions before enabling cron.
- `workforce/` is a stdlib, file-backed draft/status fleet; run `python3 workforce/smoke_test.py` offline.
- `identity/` holds templates. Keep real operator identity, memories, and continuity outside public Git.
- `skills/vire_skills/` contains imported guidance; not every referenced companion program ships here.

## Development rules

- Prefer `OLLAMA_URL`, `QDRANT_URL`, `N8N_URL`, `REDIS_URL`, and `HERMES_REALM_HOME` over embedded infrastructure.
- Keep `~/.hermes` paths only where upstream Hermes genuinely owns them.
- Never print or commit tokens, passwords, private account identifiers, recordings, or raw memory exports.
- Keep the trusted task queue private. Shell and HTTP tasks require explicit opt-in environment switches.
- Require operator confirmation for destructive actions, external-account changes, and purchases.
- Validate Python syntax and run `workforce/smoke_test.py` after changes.
