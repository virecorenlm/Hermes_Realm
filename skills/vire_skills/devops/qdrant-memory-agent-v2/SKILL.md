---
name: qdrant-memory-agent-v2
description: "Use when classifying Qdrant search results and routing them to source review or a build queue."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Memory agent pattern

This optional companion pattern combines semantic and keyword retrieval, groups chunks by source, and proposes the next read-only review step. Configure `OLLAMA_URL` and `QDRANT_URL`; verify collection dimensions match the embedding model. Reassemble full sources before modifying code. Store source hashes and deterministic identifiers so repeat indexing can be checked. The companion agent is not shipped or started by this repository.
