# Hermes Realm

Hermes Realm is a collection of scripts, skills, and patterns that extend [Hermes Agent](https://github.com/NousResearch/hermes) with optional voice, vector memory, vision experiments, scheduled status pulses, a trusted local task queue, and a file-backed workforce. It is an integration kit, not an installer or a fork of Hermes. Install Hermes separately using its upstream instructions.

## Start on one computer

Python 3 is needed for the scripts. `workforce/` uses only the Python standard library; other components have their own optional dependencies. From a checkout:

```bash
python3 workforce/smoke_test.py
python3 workforce/queen_orchestrator.py init
python3 workforce/queen_orchestrator.py status
```

The workforce writes local inbox, outbox, and report files under `workforce/`. Its agents draft and report; Shopify is parked by default. Reachability checks use local URLs and may report a service down when that optional service is not installed. Set `VIRE_WORKFORCE_SKIP_NETWORK=1` for offline checks.

## Configuration

Copy `.env.example` to a private location and set only the variables needed by your components. These standalone scripts read process environment variables; they do not automatically source `.env.example`. Hermes Realm state and secrets default to `${XDG_CONFIG_HOME:-$HOME/.config}/hermes-realm/`, with `HERMES_REALM_HOME` as an override. Put local credential files under its `secrets/` directory, restrict permissions, and keep them out of Git. Upstream Hermes paths such as `~/.hermes` remain Hermes owned.

Local defaults are `OLLAMA_URL=http://127.0.0.1:11434`, `QDRANT_URL=http://127.0.0.1:6333`, `N8N_URL=http://127.0.0.1:5678`, and `REDIS_URL=redis://127.0.0.1:6379`. Install only the services your selected scripts use. Point those URL variables at trusted remote hosts for an optional multi-host setup. `TTS_URL` is reserved for integrations that use an HTTP TTS service; the included Piper scripts use a local binary and `PIPER_MODEL`.

## Components

| Area | Representative entry point | Requirements and status |
| --- | --- | --- |
| Workforce | `python3 workforce/queen_orchestrator.py status` | stdlib; file-backed drafts and status |
| Memory sync | `python3 scripts/memory_sync_qwen3.py` | `requests`, Ollama embedding model, Qdrant; writes vectors |
| Voice diagnostics | `python3 scripts/voice_stack_check.py` | Piper, Whisper and audio dependencies; local hardware |
| Voice loop | `python3 scripts/voice_pipeline_v3.py` | Hermes CLI, Piper model, microphone, speaker, Python audio packages |
| Trusted task queue | `python3 scripts/vire_agent.py` | `requests`; accepts JSON only from trusted local writers |
| Meta Page helper | `python3 scripts/meta_facebook_poster.py --check` | configured Page credentials; `--post` publishes externally |

For the voice loop set `PIPER_MODEL` to an installed ONNX voice, and optionally `HERMES_EXE` to the Hermes executable. Hermes voice tool approval remains enabled by default; `HERMES_VOICE_YOLO=1` is an explicit override for a trusted installation. The included identity files are templates. Copy and customize them privately if you want persistent agent identity. `skills/vire_skills/` contains reusable guidance; several imported skills describe optional tools outside this repository and should be adapted before use. `origin/` explains why private archives are absent.

## Safety and integrations

The queue runner's `bash` and `http` task types are disabled unless `REALM_ALLOW_SHELL_TASKS=1` or `REALM_ALLOW_HTTP_TASKS=1` is deliberately set. Model-generated plans go to `tasks/pending/`; review each JSON file before promoting it into `tasks/queue/`. Keep queue write access restricted even then. Confirm destructive operations, external-account changes, and all purchases explicitly. Meta, Shopify, TikTok, Gmail, Telegram, n8n, Redis, and Qdrant are optional. Use `SHOPIFY_STORE`, `META_PAGE_ID`, `META_IG_ACCOUNT_ID`, `TIKTOK_OPEN_ID`, `GMAIL_USER`, and corresponding token variables or private credential files where relevant. No account is preconfigured.

## Experimental areas

Voice hardware mappings, wake-word paths, vision/Hailo scripts, cron pulses, and imported skills are reference implementations. Some imported skills point to companion scripts or MCP servers that are not shipped here. Check local device names, dependencies, collection schemas, and permissions before running them. The offline workforce smoke test is the main automated verification supplied by this repository.

See [architecture.md](architecture.md), [docs/NETWORK_SERVICES.md](docs/NETWORK_SERVICES.md), and [PUBLIC_SANITIZATION_REPORT.md](PUBLIC_SANITIZATION_REPORT.md).
