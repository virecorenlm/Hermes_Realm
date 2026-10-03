---
name: vire-memory-systems
description: "Use when configuring or debugging optional Qdrant and Redis memory layers."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Memory systems

Hermes retains its own session state. Realm examples can add Redis checkpoints and Qdrant semantic memory. Install each only when needed. Default service URLs are loopback and may be moved to trusted remote hosts with `REDIS_URL` and `QDRANT_URL`.

Before writing vectors, inspect the collection's configured dimension and measure the selected embedding model's output dimension. Never mix incompatible embeddings in one collection. Keep sync state under `HERMES_REALM_HOME/state/`, back up Qdrant with snapshots, and retain raw personal memory outside public Git. `scripts/memory_sync_qwen3.py` is the included sync example; companion clients mentioned in older notes are not included.
