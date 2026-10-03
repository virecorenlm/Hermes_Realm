# Hermes Realm architecture

Hermes Agent is the upstream runtime. This repository adds optional layers around it: identity templates, voice input/output, vector-memory sync, file-backed workforce tasks, trusted queue execution, monitoring pulses, and integration guidance. No single launcher starts all components.

## Single-computer layout

The checkout contains source, examples, and public templates. `HERMES_REALM_HOME` selects private Realm state and secrets; its default is `${XDG_CONFIG_HOME:-$HOME/.config}/hermes-realm`. Hermes keeps its own runtime files under its upstream directory. Run only the services used by a selected component:

- Ollama for local generation or embeddings (`OLLAMA_URL`).
- Qdrant for vector memory (`QDRANT_URL`).
- n8n for optional workflow automation (`N8N_URL`).
- Redis for optional checkpoint state (`REDIS_URL`).
- Piper and Whisper for local voice; Hailo for optional accelerator experiments.

Default URLs resolve to loopback. For optional multi-host deployments, configure the URL variables for trusted remote hosts. Do not assume a fixed machine count or node role. Secure remote services and preserve their native protocols.

## Trust boundaries

The workforce writes drafts and local reports, with external integrations parked or opt-in. The queue runner reads JSON from a trusted local directory and has explicit shell and HTTP opt-in switches. Model-generated plans and voice commands do not grant broad permission. Destructive changes, external-account mutations, and spending require explicit operator authorization. Credentials stay in local environment or private files beneath the Realm configuration directory; public examples contain placeholders only.

## Persistence and limits

Identity templates show how to keep continuity without shipping personal history. Memory sync writes embeddings to Qdrant when enabled; scheduled pulses and checkpoint scripts are experiments that need dependency and schema checks. Voice and vision require machine-specific device configuration. Some imported skills describe companion projects and are documentation rather than runnable components of this checkout.
