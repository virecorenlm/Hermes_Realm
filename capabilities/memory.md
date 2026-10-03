# Memory capability

Hermes owns its own conversation state under `~/.hermes`. This repository adds optional examples for semantic memory in Qdrant and checkpoint experiments using Redis. Neither service is needed for the file-backed workforce.

`scripts/memory_sync_qwen3.py` scans the upstream OpenClaw workspace memory directory and selected Markdown files, creates Ollama embeddings, and upserts them into a Qdrant collection. Configure `OLLAMA_URL` and `QDRANT_URL`; default URLs are loopback. Ensure the target collection has the vector size required by your selected embedding model before syncing. The script stores its local sync state under `HERMES_REALM_HOME/state/`.

`cron-pulses/vire_auto_checkpoint.py` is experimental. It expects upstream Hermes state, Redis, Ollama, and Qdrant. Verify the upstream database schema before scheduling it. Export Qdrant collection snapshots and back up application state using your local retention policy. Keep raw personal memories outside public Git.
