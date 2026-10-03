# Hermes Realm project map

This is a guided map of the **current checkout**, not a promise that every described integration is installed. Terms used below: **shipped** means code is in this repository; **example** means an operator must adapt and install it; **guidance** means instructions rather than an executable integration; **experimental** means the code needs local dependency, schema, permission, or hardware review.

## What Hermes Realm is

[Hermes Agent](https://github.com/NousResearch/hermes) is the upstream agent runtime and must be installed separately. Hermes Realm is a local-first collection around it: identity/continuity templates, optional voice and vector-memory scripts, a deterministic file-backed workforce, a separate trusted task runner, scheduled experiments, integration instructions, and operational examples. It is **not** a Hermes fork, installer, or unified application with one start command.

A “Realm” is the operator's chosen configuration, private state, skills, and optional services around Hermes. This checkout supplies reusable parts, not another person's live identity or infrastructure. Start on **one computer** and enable only the pieces you need. The file-backed workforce is the easiest self-contained starting point. Ollama, Qdrant, n8n, Redis, voice devices, social accounts, and additional hosts are all optional and component-specific.

## How to read this repository

1. [README.md](README.md) — quick start, trust boundaries, and optional dependencies.
2. This map — choose a subsystem and distinguish shipped code from guidance.
3. [architecture.md](architecture.md) — the short architectural contract; [.env.example](.env.example) — configuration names (not a loaded configuration file).
4. [workforce/README.md](workforce/README.md) — the lowest-dependency runnable subsystem; then its [orchestrator](workforce/queen_orchestrator.py) and [shared agent framework](workforce/common.py).
5. The relevant [capability note](capabilities/), [skill](skills/vire_skills/), or [script](scripts/). Read [CLAUDE.md](CLAUDE.md) before changing code.

## Repository at a glance

```text
Hermes_Realm/
├── scripts/                standalone configuration, queue, memory, voice, vision, Meta, forecast
├── workforce/              file-backed orchestrator, nine deterministic agents, offline smoke test
├── skills/vire_skills/     34 active SKILL.md instruction sets, including imported guidance
├── capabilities/           short capability notes; not executable plugins
├── cron-pulses/            opt-in one-shot scheduled scripts and older templates
├── integration-examples/  sample cron entries and systemd units; nothing auto-installed
├── identity/              public continuity/identity templates
├── docs/                  operations, network, hardware, recovery, and design notes
├── origin/                public explanation of omitted private origin archives
├── README.md              start here
├── PROJECT_MAP.md         this navigation document
├── architecture.md        architectural overview and trust boundaries
├── CLAUDE.md              contributor/agent working rules
├── .env.example           placeholder-only configuration reference
├── .gitignore             excludes runtime state and credential files
├── LICENSE                repository license
└── PUBLIC_SANITIZATION_REPORT.md  public release audit summary, not live configuration
```

| Area | Status | Open it when… |
| --- | --- | --- |
| [scripts/](scripts/) | Shipped, independent programs; most require optional packages or services | You want the actual implementation or an entry point for queue, memory, voice, vision, forecast, or Page posting. |
| [workforce/](workforce/) | Shipped, stdlib-only deterministic subsystem | You want dispatch, inbox/outbox processing, draft agents, or status reports. |
| [skills/vire_skills/](skills/vire_skills/) | Active instruction documents, **not automatically installed tools** | You want a procedure, guardrail, or integration recipe; verify referenced companions first. |
| [capabilities/](capabilities/) | Documentation-only | You need the memory, vision, or voice prerequisites and limits. |
| [cron-pulses/](cron-pulses/) | Optional/experimental scripts | You want scheduled weather/content/checkpoint/continuity behavior; inspect writes and dependencies first. |
| [integration-examples/](integration-examples/) | Examples only | You want to adapt a user cron entry or systemd service; no installer enables these. |
| [identity/](identity/) | Templates/context | You want a private identity and continuity record structure. |
| [docs/](docs/) | Documentation-only | You need network, hardware, sync, recovery, or design context. |
| [origin/](origin/) | Historical/contextual placeholder | You want to understand why private predecessor archives are absent. |

The root [LICENSE](LICENSE) is MIT. [PUBLIC_SANITIZATION_REPORT.md](PUBLIC_SANITIZATION_REPORT.md) records public-release cleanup and offline verification, not a live deployment audit. [docs/ARCHITECTURE_REVIEW_IDEAS.md](docs/ARCHITECTURE_REVIEW_IDEAS.md) lists possible future work; it is not a feature list.

## Core configuration and runtime boundary

[scripts/realm_config.py](scripts/realm_config.py) is the small shared configuration layer for **standalone scripts and cron pulses**. `realm_home()` chooses `HERMES_REALM_HOME`, otherwise `${XDG_CONFIG_HOME:-$HOME/.config}/hermes-realm`; `realm_path()` builds paths beneath it. The same module reads `OLLAMA_URL`, `QDRANT_URL`, `N8N_URL`, `REDIS_URL`, and `TTS_URL`. Defaults for the first four point to loopback; `TTS_URL` is empty unless supplied. [workforce/common.py](workforce/common.py) independently reads its service-probe URLs from the environment; it does not import `realm_config.py`.

[.env.example](.env.example) names optional variables and contains placeholders. Copy values into your **private process environment** or private files under the Realm home `secrets/` directory; neither the example nor a root `.env` is automatically sourced by the Python programs. [README.md](README.md) explains the default path and [.gitignore](.gitignore) excludes filled `.env` files, secrets, and generated state. The [systemd examples](integration-examples/systemd_units/) show `EnvironmentFile=` for an operator-supplied file. Keep permissions tight. `~/.hermes` is upstream Hermes-owned state, not Realm home; some scripts also expect an upstream `~/.openclaw/workspace` layout.

These URLs **select endpoints**, not implementations: setting `QDRANT_URL` does not install Qdrant, create its collections, or authenticate a remote server. `N8N_URL` supports workforce health checks and skill recipes; this checkout has no n8n workflow JSON library. `TTS_URL` describes a possible HTTP bridge, but shipped speech code invokes a **local Piper binary**, not that URL. Use trusted, secured endpoints if you move any service off loopback. See [docs/NETWORK_SERVICES.md](docs/NETWORK_SERVICES.md).

## How the pieces fit

```text
operator ──> upstream Hermes (separate install; owns its sessions and gateway)
                │
                ├── optional Realm identity templates / installed skills
                └── optional voice loop ──> Hermes CLI ──> local Piper

operator ──> workforce queen ──> per-agent inbox ──> deterministic draft/status agent
                                      └── outbox + JSON data + processed input

trusted local writer ──> Realm task queue ──> queue runner ──> opted-in task type

optional, independent: memory sync / cron pulses / Meta helper / vision example
                         │
                         └── configured local or remote services and accounts
```

There is **no automatic bridge** from workforce outboxes to the trusted queue, from a skill to an installed server, or from these scripts to a single Realm daemon. Wiring such flows is deployment-specific and must preserve the permission boundary.

## Workforce: orchestration and nine agents

[workforce/queen_orchestrator.py](workforce/queen_orchestrator.py) implements `init`, `status`, `seed`, `dispatch`, `run-agent`, `tick-all`, and `synthesize`. It uses [workforce/common.py](workforce/common.py) for the agent registry, layout, inbox parsing, result rendering, service probes, logging, and parked-agent settings. Each agent has `agents/<name>/inbox/`, `outbox/`, `data/`, and `processed/` directories **created under `workforce/` at runtime**. These runtime directories are ignored by Git. Inputs can be JSON or text; a tick writes Markdown and JSON results, then moves the input to `processed/`. This is one-pass file processing, not a long-running scheduler or distributed queue.

`seed` adds sample tasks only for unparked agents. `tick-all` runs each unparked agent once in a subprocess. `dispatch` writes a task to an inbox even if its agent is parked, but `run-agent` and `tick-all` refuse/skip parked agents. `shopify` is parked by default via `VIRE_WORKFORCE_PARKED_AGENTS=shopify`. Unparking it permits its **plan-only** agent to run; it does not enable Shopify API writes. `status` writes a timestamped report and performs TCP/HTTP GET probes of configured Ollama, n8n, and Qdrant URLs (plus optional dashboard, Chroma, PostgreSQL URLs); set `VIRE_WORKFORCE_SKIP_NETWORK=1` to mark probes skipped offline. `synthesize` summarizes counts and latest outbox text; it does not combine plans with an LLM or execute them. The agents' common `safe_mode` result is `true`.

| Agent | Purpose / input | Output from current code | External actions? |
| --- | --- | --- | --- |
| [`network`](workforce/network_agent.py) | Service reachability task | TCP and HTTP GET results, suggested investigation | Read-only network probes, unless skipped |
| [`n8n`](workforce/n8n_agent.py) | n8n health/inventory-planning task | Reachability result and manual next step | Read-only configured-service probes; **no workflow inventory API call** |
| [`content`](workforce/content_agent.py) | Topic from task/payload | Fishing/social outline and draft CTA | None; no publication |
| [`shopify`](workforce/shopify_agent.py) | Catalog/relaunch task | Offline checklist | None; parked by default, plan-only even unparked |
| [`seo`](workforce/seo_agent.py) | SEO task/payload | Generic on-page checklist | None; no crawl |
| [`crm`](workforce/crm_agent.py) | Follow-up task | Draft segmentation/follow-up plan | None; no contact or CRM mutation |
| [`email`](workforce/email_agent.py) | Email task and optional subject | Draft email outline | None; no IMAP/SMTP or send |
| [`sheets`](workforce/sheets_agent.py) | KPI/reporting task | Proposed column schema | None; no spreadsheet API or CSV file export |
| [`hailo`](workforce/hailo_agent.py) | Vision inventory task | Local HEF filename inventory and planning | Local filesystem read only; no inference |

Start with `python3 workforce/smoke_test.py` (copies sources into a temporary directory; no network), then `python3 workforce/queen_orchestrator.py init`. `python3 workforce/queen_orchestrator.py status` creates a report under `workforce/reports/`; use the skip variable if optional services are absent. [workforce/workforce_status.py](workforce/workforce_status.py) is a thin status entry point. [workforce/memory/business_state.md](workforce/memory/business_state.md) is a small checked-in policy note; runtime per-agent memories are created by `init` and are not a Qdrant memory system.

## Trusted task queue: a different subsystem

[scripts/vire_agent.py](scripts/vire_agent.py) is an independent polling runner (`python3 scripts/vire_agent.py`, after reviewing its local queue permissions). It watches `HERMES_REALM_HOME/tasks/queue/*.json` every five seconds and writes completed tasks to `tasks/done/`, failed tasks to `tasks/failed/`, and logs under `logs/`. It needs `requests`; Ollama and Qdrant are needed for particular task types and optional result-memory writes. It is **not** invoked by the workforce queen.

| Stage / task type | Current behavior and gate |
| --- | --- |
| `plan` | Asks Ollama for JSON steps and writes them to `tasks/pending/`; does **not** enqueue or execute them. A trusted operator must inspect and deliberately promote each step. |
| `ollama` | Sends a prompt to the configured Ollama CLI host; a trusted queue writer can run it without an extra switch. |
| `remember` | Embeds through Ollama and attempts to write to Qdrant `vire_memory`; collection/schema must already be suitable. |
| `bash` | Runs a shell command **only** with `REALM_ALLOW_SHELL_TASKS=1`; shell execution is unrestricted once that global gate is enabled, so queue writers must be trusted. |
| `http` | Makes the specified HTTP request **only** with `REALM_ALLOW_HTTP_TASKS=1`; this is not a read-only or domain allowlist. |

The runner is a **trusted-input** mechanism, not a sandbox or approval UI. Moving a reviewed JSON file into `queue/` is the manual review step; the code does not verify a reviewer signature. Successful outputs (except `remember`) also attempt an optional Qdrant memory write. Keep shell/HTTP gates off unless specifically needed; confirm destructive changes, account mutations, and spending with the operator independently.

## Skills: instruction sets, not installed integrations

Each active skill is a `SKILL.md` file under [skills/vire_skills/](skills/vire_skills/). Its frontmatter gives a name and description; the body gives procedures or architectural guidance to an agent that has been given the skill. The repository does **not** include a skill installer/registration command, and merely checking out these files does not activate them in Hermes. `openclaw-imports/` is a source grouping for retained guidance, **not an archive**. There are 34 active skill documents in this tree; archived snapshots were removed during public preparation. The table indexes all 34. “Relevant” does not mean the described helper exists here.

### Realm, safety, and continuity

| Skill | Purpose | When relevant |
| --- | --- | --- |
| [`vire`](skills/vire_skills/openclaw-imports/vire/SKILL.md) | Entry index and cross-cutting boundaries | Choosing a focused Realm skill |
| [`vire-realm-subsystems`](skills/vire_skills/openclaw-imports/vire-realm-subsystems/SKILL.md) | Optional subsystem pattern directory | Deciding what to add around Hermes |
| [`vire-autonomy-modes`](skills/vire_skills/openclaw-imports/vire-autonomy-modes/SKILL.md) | Operator-controlled permission model | Setting read/write/external-action boundaries |
| [`vire-file-management`](skills/vire_skills/openclaw-imports/vire-file-management/SKILL.md) | Safe organization and secret handling | Moving or cleaning local files |
| [`vire-infra-doc-maintenance`](skills/vire_skills/openclaw-imports/vire-infra-doc-maintenance/SKILL.md) | Keep local deployment notes accurate | Documenting changed services/hardware |
| [`vire-consciousness-pulse`](skills/vire_skills/openclaw-imports/vire-consciousness-pulse/SKILL.md) | Review scheduled reflection/status experiments | Considering a cron pulse |

### Memory and state-graph patterns

| Skill | Purpose | When relevant |
| --- | --- | --- |
| [`vire-memory-systems`](skills/vire_skills/openclaw-imports/vire-memory-systems/SKILL.md) | Optional Redis/Qdrant memory design | Adding or debugging persistence |
| [`qdrant-memory-agent-v2`](skills/vire_skills/devops/qdrant-memory-agent-v2/SKILL.md) | Retrieval-to-review routing pattern; no agent shipped | Designing a memory review companion |
| [`qdrant-source-reassembler`](skills/vire_skills/devops/qdrant-source-reassembler/SKILL.md) | Reconstruct chunked sources; no implementation shipped | Needing full-document evidence |
| [`qdrant-build-candidate-librarian`](skills/vire_skills/devops/qdrant-build-candidate-librarian/SKILL.md) | Report-only build-candidate pattern | Mining retrieved notes safely |
| [`realm-state-graph`](skills/vire_skills/devops/realm-state-graph/SKILL.md) | Report-only dependency graph pattern; no generator shipped | Mapping scripts/services |
| [`realm-state-graph-operator`](skills/vire_skills/devops/realm-state-graph-operator/SKILL.md) | Prioritize graph findings without source edits | Reviewing such a graph |

### Infrastructure, automation, and tooling

| Skill | Purpose | When relevant |
| --- | --- | --- |
| [`vire-local-llm-runtime`](skills/vire_skills/mlops/vire-local-llm-runtime/SKILL.md) | Ollama/model readiness guidance | Configuring local generation or embeddings |
| [`vire-local-mcp-services`](skills/vire_skills/mcp/vire-local-mcp-services/SKILL.md) | MCP server inspection and registration guidance | Integrating an external MCP server |
| [`vire-n8n-automation`](skills/vire_skills/openclaw-imports/vire-n8n-automation/SKILL.md) | n8n API/webhook recipes and workflow ideas | Building your own n8n automation |
| [`local-tool-authoring-and-safety`](skills/vire_skills/devops/local-tool-authoring-and-safety/SKILL.md) | Tool validation, secrets, and side-effect review | Authoring an optional tool/router |
| [`anti-ai-slop-code-standards`](skills/vire_skills/software-development/anti-ai-slop-code-standards/SKILL.md) | Code quality and permission checklist | Reviewing generated code |

### Voice, vision, and remote interaction

| Skill | Purpose | When relevant |
| --- | --- | --- |
| [`vire-voice-stack`](skills/vire_skills/openclaw-imports/vire-voice-stack/SKILL.md) | Local voice-stack setup guidance | Debugging the shipped voice scripts |
| [`local-voice-tts-services`](skills/vire_skills/media/local-voice-tts-services/SKILL.md) | Piper and optional HTTP TTS guidance | Selecting a voice output path |
| [`hailo-8-vision-inference`](skills/vire_skills/mlops/hailo-8-vision-inference/SKILL.md) | Hailo inference and postprocessing patterns | Building a hardware vision pipeline |
| [`vire-telegram-gateway`](skills/vire_skills/openclaw-imports/vire-telegram-gateway/SKILL.md) | Upstream Hermes Telegram gateway checks | Configuring remote messaging in Hermes |

### Business and external accounts

| Skill | Purpose | When relevant |
| --- | --- | --- |
| [`vire-gmail`](skills/vire_skills/openclaw-imports/vire-gmail/SKILL.md) | SMTP/IMAP and App Password recipe | Configuring an operator's Gmail account |
| [`vire-shopify-management`](skills/vire_skills/openclaw-imports/vire-shopify-management/SKILL.md) | Shopify API and proposed workflow recipes | Managing a configured store, after API review |
| [`vire-lure-photo-pipeline`](skills/vire_skills/openclaw-imports/vire-lure-photo-pipeline/SKILL.md) | Photo-to-Shopify-draft design | Prototyping a draft-only product intake |
| [`vire-product-scraping`](skills/vire_skills/openclaw-imports/vire-product-scraping/SKILL.md) | Own-store-first product data rules | Collecting reference/product metadata |
| [`vire-capital-ledgers`](skills/vire_skills/openclaw-imports/vire-capital-ledgers/SKILL.md) | Manual ledger and paper-trial boundaries; no ledger CLI shipped | Designing finance experiments |
| [`vire-content-strategy`](skills/vire_skills/openclaw-imports/vire-content-strategy/SKILL.md) | Example content pillars/schedule | Planning reviewed store content |
| [`vire-facebook-instagram`](skills/vire_skills/openclaw-imports/vire-facebook-instagram/SKILL.md) | Graph API posting examples | Adapting Page/Instagram publishing |
| [`meta-social-posting`](skills/vire_skills/social-media/meta-social-posting/SKILL.md) | Meta permissions and posting workflow | Checking a Page token or designing reviewed posts |
| [`vire-tiktok`](skills/vire_skills/openclaw-imports/vire-tiktok/SKILL.md) | TikTok Content Posting API recipe | Building an operator-approved upload flow |

### Content and media

| Skill | Purpose | When relevant |
| --- | --- | --- |
| [`vire-graphic-design`](skills/vire_skills/openclaw-imports/vire-graphic-design/SKILL.md) | GIMP/Inkscape/ImageMagick examples | Producing graphics with installed tools |
| [`vire-video-production`](skills/vire_skills/openclaw-imports/vire-video-production/SKILL.md) | OBS/FFmpeg command examples | Capturing or editing media manually |
| [`vire-reels-pipeline`](skills/vire_skills/openclaw-imports/vire-reels-pipeline/SKILL.md) | Short-video workflow design | Planning a staged reels workflow |
| [`vire-media-sorting`](skills/vire_skills/openclaw-imports/vire-media-sorting/SKILL.md) | Copy-only media sorting design | Building a separate media organizer |

Several skill bodies still refer to `references/`, `assets/`, shell wrappers, n8n workflow files, a tool router, or a `hermes-agent`/`native-mcp` skill that are **not in this checkout**. Read those as adaptation notes, not executable instructions. In particular, there is no bundled Shopify upsert/price wrapper, TikTok posting wrapper, Reels generator, MCP server, state-graph generator, or ready-made n8n workflow library.

## Memory and knowledge

| Piece | Shipped behavior | Prerequisites / limits |
| --- | --- | --- |
| Upstream Hermes state | Owned by separately installed Hermes (`~/.hermes`); not implemented here | Check upstream layout/version before reading its SQLite files. |
| [Memory sync](scripts/memory_sync_qwen3.py) | Scans `~/.openclaw/workspace/memory` and selected curated Markdown, chunks text, gets `qwen3-embedding:latest` vectors from Ollama, upserts Qdrant `vire_memory`, records file hashes beneath Realm home `state/` | Requires `requests`, Ollama model, pre-existing compatible Qdrant collection. Incremental by file hash; `--force` reprocesses. |
| [Queue memory](scripts/vire_agent.py) and [voice memory](scripts/voice_pipeline_v3.py) | Independently attempt embeds/upserts to `vire_memory` | Optional services; failure does not establish a complete recall system. |
| [Auto-checkpoint](cron-pulses/vire_auto_checkpoint.py) | Experimental topic checkpoint from upstream SQLite messages; uses Redis state, Ollama, Qdrant `vire_memories`, and a Markdown log; has `--dry-run` | Assumes specific upstream database schema and model/collection compatibility. Review before scheduling. |
| [Pulse scripts](cron-pulses/) | Some count or write to `vire_memories` / `vire_brain`, local logs, or task files | Multiple collections and state conventions; not a single unified memory schema. |
| [Memory capability](capabilities/memory.md) and memory skills | Guidance on dimension checks, backups, and optional retrieval patterns | Retrieval/reassembly companion agents mentioned by skills are not shipped. |

Qdrant stores vectors; Ollama supplies embeddings. Redis is only used by optional checkpoint behavior, not by the workforce. The file-backed workforce's `memory.md` files are local text notes, not a semantic search layer. Configure Qdrant collections and embedding dimensions deliberately; the scripts do not provision a unified knowledge platform.

## Voice and vision

[scripts/voice_pipeline_v3.py](scripts/voice_pipeline_v3.py) contains two capture paths: a sounddevice silence-detection callback and the **actual `run()` loop**, which repeatedly captures fixed five-second clips with `arecord`. It transcribes with faster-whisper or whisper.cpp, routes a small allowlist via [scripts/voice_command_router.py](scripts/voice_command_router.py), otherwise calls `hermes chat --query ... --quiet --source tool`, and speaks with local Piper via `aplay`. The router can check Qdrant/Hailo and has an explicitly gated companion defensive-scan path; it does not execute arbitrary transcript text as a shell command. `HERMES_EXE` selects the CLI; `HERMES_VOICE_YOLO=1` explicitly adds Hermes `--yolo` and should not be a default. Successful conversations attempt optional Qdrant storage.

The current live loop hardcodes ALSA input `hw:2,0` despite device variables used by the alternate sounddevice path; configure or adapt the code for your hardware before calling it portable. A “wake” prefix is stripped **after transcription** by the router; the live loop does **not** gate listening on an OpenWakeWord detector. [scripts/voice_stack_check.py](scripts/voice_stack_check.py) probes dependencies, models, devices, and OpenWakeWord loading but has a different default Whisper backend from the live pipeline. [scripts/voice_test_chain.py](scripts/voice_test_chain.py) is a hardware smoke chain. [scripts/piper_speak.sh](scripts/piper_speak.sh) is a simpler Piper/PipeWire wrapper. Piper/Whisper models, binaries, audio hardware, and upstream Hermes are not bundled; `PIPER_MODEL` is required for speech. See [capabilities/voice.md](capabilities/voice.md).

[scripts/hailo_vision_capture.py](scripts/hailo_vision_capture.py) is an optional Hailo/OpenCV webcam inference example with fixed `/dev/video0` and HEF search under a user's Downloads folder. It is **not** the `hailo` workforce agent (which only inventories files). It needs compatible hardware, vendor runtime, model output shape, and camera paths. See [capabilities/vision.md](capabilities/vision.md) and the Hailo skill before trying it.

## Automation and deployment examples

Nothing under [cron-pulses/](cron-pulses/) schedules itself. [daily_bait_tip.py](cron-pulses/daily_bait_tip.py) prints a draft tip; [weather_alert_monitor.py](cron-pulses/weather_alert_monitor.py) analyzes a configured NWS hourly URL and prints condition alerts. [daily_fishing_forecast.py](cron-pulses/daily_fishing_forecast.py) and [scripts/fishing_forecast_pipeline.py](scripts/fishing_forecast_pipeline.py) are wrappers around an external `forecast` module selected by `FISHING_FORECAST_DIR`; that module is **not shipped**. The cron comment about Hermes forwarding output to Telegram describes an operator-configured upstream workflow, not a scheduler in this repository.

The [auto-checkpoint](cron-pulses/vire_auto_checkpoint.py) and three [pulse](cron-pulses/vire_conscious_pulse.py) [variants](cron-pulses/vire_conscious_pulse_v2.py) ([writing edition](cron-pulses/vire_conscious_pulse_writing.py)) are experiments, not one canonical service. They can write local notes/state, query Qdrant, create tasks, copy/quarantine files, or capture/speak depending on the variant. Inspect side effects and their Linux/upstream assumptions before scheduling. [cron-pulses/templates/](cron-pulses/templates/) retains alternate pulse templates for adaptation, not additional installed jobs.

[integration-examples/cron_jobs.md](integration-examples/cron_jobs.md) shows user-crontab examples. [integration-examples/systemd_units/vire_agent.service](integration-examples/systemd_units/vire_agent.service) and [vire_voice.service](integration-examples/systemd_units/vire_voice.service) are example services requiring edited checkout paths, environment files, and dependencies. [redis_bulletproof.service](integration-examples/systemd_units/redis_bulletproof.service) is a hardware-specific Redis drop-in example, **not** a general default. See [docs/EMERGENCY_ROLLBACK.md](docs/EMERGENCY_ROLLBACK.md) before changing persistent services.

## External integration matrix

“Required?” means required by the **named component**, never by the entire repository.

| Integration | Used for / actual support | Required? | Configuration / boundary |
| --- | --- | --- | --- |
| Hermes Agent/CLI | Upstream chat, session state, optional gateway; voice calls CLI | Only for Hermes-backed flows | Install separately; `HERMES_EXE` for voice; verify upstream CLI compatibility |
| Ollama | Queue prompting, embeddings, memory/pulse experiments, workforce probe | For those scripts | `OLLAMA_URL`; install suitable models separately |
| Qdrant | Vector upsert/count/query examples; workforce probe | For vector features | `QDRANT_URL`; create compatible collections yourself |
| Redis | Auto-checkpoint cursor/state | Only for checkpoint | `REDIS_URL` |
| n8n | Workforce reachability and skill-level API/webhook recipes | No | `N8N_URL`; no shipped workflow JSON or automatic scheduler |
| Piper / Whisper | Local speech output and transcription | Only for voice | `PIPER_MODEL`, Whisper backend/model/bin variables; binaries and models external |
| HTTP TTS | Companion bridge described by a skill | No; no shipped client | `TTS_URL` is reserved, not consumed by live voice code |
| Gmail | SMTP/IMAP skill recipe; workforce `email` is draft-only | No | `GMAIL_USER`, `GMAIL_APP_PASSWORD`; account/operator approval |
| Shopify | API skill recipes; workforce `shopify` is offline planning | No | `SHOPIFY_STORE`, `SHOPIFY_ACCESS_TOKEN`, API version; no shipped store client |
| Meta / Facebook | Shipped Page check/post helper plus skill recipes | No | `META_PAGE_ID`, `META_PAGE_ACCESS_TOKEN` (or aliases); [helper](scripts/meta_facebook_poster.py) `--post` publishes externally |
| Instagram | Meta Graph recipes in skills only | No | `META_IG_ACCOUNT_ID` and valid Graph credentials; no shipped IG poster |
| TikTok | Content Posting API skill recipe only | No | `TIKTOK_OPEN_ID`, `TIKTOK_ACCESS_TOKEN`; no shipped upload wrapper |
| Telegram | Upstream Hermes gateway skill guidance | No | Upstream Hermes bot/gateway settings, not Realm gateway code |
| MCP servers | Registration/security guidance only | No | Configure upstream Hermes and a separately installed server |
| Hailo / camera | Vision example and local HEF inventory agent | No | Vendor runtime, HEF, camera; paths/device must match host |
| NWS hourly forecast | Weather monitor HTTP read | No | `NWS_HOURLY_URL`, optional `WEATHER_USER_AGENT` |

[scripts/meta_facebook_poster.py](scripts/meta_facebook_poster.py) defaults to a private `secrets/facebook.env` beneath Realm home and accepts environment aliases. Its `--check` performs live Graph API reads; `--post --message-file <file>` is a real external Page write, not a dry run. The business skills are largely procedures; do not infer that their named workflows or scripts were installed. [docs/NETWORK_SERVICES.md](docs/NETWORK_SERVICES.md) lists local endpoint defaults.

## Capabilities, identity, and continuity

[capabilities/memory.md](capabilities/memory.md), [vision.md](capabilities/vision.md), and [voice.md](capabilities/voice.md) are short **documentation** notes, not a capability registry or executable plugin framework. A **skill** is a reusable instruction file; a **script** is code you can invoke; a **workforce agent** is a deterministic inbox processor. This repository has no common runtime that discovers and loads all four categories.

[identity/AGENT_IDENTITY.md](identity/AGENT_IDENTITY.md) is a public-safe persona/boundary template; [AGENT_CHRONICLE.md](identity/AGENT_CHRONICLE.md) is a suggested change-history structure; [HERMES_REALM_ORIGIN.md](identity/HERMES_REALM_ORIGIN.md) explains the reusable continuity pattern. These files do not automatically become Hermes system prompts or persistent memory. The voice script loads a privately configured identity file or the repository fallback into `SYSTEM_PROMPT`, but its current `chat()` path sends a separate fixed instruction to Hermes and **does not pass that loaded prompt**. Upstream Hermes owns its own identity/session behavior. Keep your real continuity records and raw conversations private. [origin/README.md](origin/README.md) explains why predecessor archives are deliberately absent.

## Single-machine default and optional multi-host use

**Core starting path:** a checkout plus Python 3 can run the offline [workforce smoke test](workforce/smoke_test.py) and the file-backed workforce. The README's startup commands do **not** imply any model or vector server is running. Other standalone programs are opt-in and have their own dependencies. No root `requirements.txt`, installer, or all-in-one launcher is supplied.

**Optional local services:** add Ollama when you need model calls/embeddings, Qdrant for vectors, Redis for checkpoint state, n8n for workflows you build, and Piper/Whisper/audio devices for voice. The default URLs are loopback. You can put any supported service on another trusted host by changing its URL environment variable and securing transport/access. This changes where a client connects; it does not create a mandatory multi-node topology. See [docs/HARDWARE_MAP.md](docs/HARDWARE_MAP.md) and [docs/WINDOWS_PI_SYNC.md](docs/WINDOWS_PI_SYNC.md) for deployment considerations rather than a prescribed fleet.

## I want to change X — where do I go?

| I want to… | Start here |
| --- | --- |
| Change standalone service URLs or Realm home | [scripts/realm_config.py](scripts/realm_config.py), [.env.example](.env.example); workforce probes separately use [workforce/common.py](workforce/common.py) |
| Add/change a workforce agent | [workforce/common.py](workforce/common.py) registry/layout, [workforce/queen_orchestrator.py](workforce/queen_orchestrator.py), an existing agent, [workforce/smoke_test.py](workforce/smoke_test.py) |
| Change workforce dispatch/reporting | [workforce/queen_orchestrator.py](workforce/queen_orchestrator.py), [workforce/common.py](workforce/common.py) |
| Change trusted task types or gates | [scripts/vire_agent.py](scripts/vire_agent.py); review queue writer permissions |
| Add or adapt a skill | [skills/vire_skills/](skills/vire_skills/); use an existing `SKILL.md` structure and verify references |
| Change Qdrant ingestion | [scripts/memory_sync_qwen3.py](scripts/memory_sync_qwen3.py), [capabilities/memory.md](capabilities/memory.md) |
| Change voice input/output or router | [scripts/voice_pipeline_v3.py](scripts/voice_pipeline_v3.py), [scripts/voice_command_router.py](scripts/voice_command_router.py), [capabilities/voice.md](capabilities/voice.md) |
| Change vision example | [scripts/hailo_vision_capture.py](scripts/hailo_vision_capture.py), [capabilities/vision.md](capabilities/vision.md) |
| Add scheduled work | [cron-pulses/](cron-pulses/), [integration-examples/cron_jobs.md](integration-examples/cron_jobs.md) |
| Add an account integration | [scripts/meta_facebook_poster.py](scripts/meta_facebook_poster.py) for the one shipped Page helper; [skills/vire_skills/](skills/vire_skills/) for recipes |
| Adapt service startup | [integration-examples/systemd_units/](integration-examples/systemd_units/) |
| Understand architecture or rollback | [architecture.md](architecture.md), [docs/EMERGENCY_ROLLBACK.md](docs/EMERGENCY_ROLLBACK.md) |
| Configure secrets | [.env.example](.env.example), [README.md](README.md), [docs/NETWORK_SERVICES.md](docs/NETWORK_SERVICES.md) |

## Experimental and external-setup checklist

- **Live services/accounts:** Ollama models, Qdrant collections, Redis, n8n, social/Gmail/Shopify/TikTok credentials, Telegram gateway, and MCP servers must be installed/configured separately. The public sanitization report documents offline tests, not live-account validation.
- **Hardware:** voice requires a usable ALSA/PipeWire/audio stack and installed Piper/Whisper models; wake-word detection is diagnostic-only in this checkout. Hailo inference requires compatible hardware, HEF, camera, and vendor runtime. Current live voice and vision examples retain device/path assumptions to adapt locally.
- **Companion gaps:** the forecast module, many skill `references/` documents and wrappers, proposed n8n workflows, dashboard, MCP servers, state-graph tooling, and a media/Reels generation pipeline are not shipped here.
- **Schema/version assumptions:** memory scripts refer to different Qdrant collections and embeddings; auto-checkpoint assumes an upstream SQLite schema; voice expects particular Hermes CLI flags. Verify versions and backup state before enabling background jobs.
- **Write surfaces:** `vire_agent.py`, pulse variants, memory sync, and Meta `--post` can write locally or externally. The workforce agents stay in safe draft/probe mode, but its status command still probes network unless skipped. Read code and obtain operator approval for effects outside your workspace.

## Terminology

| Term | Meaning here |
| --- | --- |
| Hermes | Separately installed upstream agent runtime/CLI/gateway. |
| Realm | Operator-defined local-first layer of configuration, state, scripts, skills, and optional services around Hermes. |
| Skill | A `SKILL.md` instruction set; not evidence of an installed tool. |
| Capability | A short note under `capabilities/`, not an executable plugin. |
| Workforce | The stdlib file-backed subsystem in `workforce/`. |
| Agent | Here, usually one deterministic workforce inbox processor; not necessarily an autonomous LLM worker. |
| Queen | The workforce orchestrator that dispatches, ticks, probes, and reports. |
| Pulse | An optional one-shot script intended for operator-reviewed scheduling. |
| Task | A workforce inbox item **or** a separate trusted-queue JSON item; the two formats/paths are not automatically bridged. |
| Queue | The trusted task runner's `tasks/queue/`, distinct from workforce inboxes. |
| Identity / continuity | Private operator-chosen prompt/context and history, illustrated by public templates. |
| Memory | Could mean local text notes, upstream session state, Redis checkpoints, or Qdrant vectors; check the component. |
