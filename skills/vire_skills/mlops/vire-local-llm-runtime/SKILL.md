---
name: vire-local-llm-runtime
description: "Use when checking a local or configured remote Ollama runtime and embedding model."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Local model runtime

Start with Ollama on the same computer at `OLLAMA_URL=http://127.0.0.1:11434`. A remote host is optional. Check `/api/tags` for installed models before use, then make a small generation or embedding call. Do not assume a particular model, account, subscription, or accelerator is available. Match embedding output dimensions to the target Qdrant collection.

Keep provider credentials out of logs and Git. If a remote endpoint is used, verify its transport security and access controls.
