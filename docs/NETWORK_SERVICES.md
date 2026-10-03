# Optional local services

Hermes Realm runs scripts independently. Enable only the services your workflow needs.

| Service | Default | Used by |
| --- | --- | --- |
| Ollama | `OLLAMA_URL=http://127.0.0.1:11434` | embeddings and local model calls |
| Qdrant | `QDRANT_URL=http://127.0.0.1:6333` | vector memory examples |
| n8n | `N8N_URL=http://127.0.0.1:5678` | optional automation and status checks |
| Redis | `REDIS_URL=redis://127.0.0.1:6379` | optional checkpoint experiments |
| Piper HTTP | `TTS_URL` unset | optional remote voice service |

Set a URL to a trusted remote host for an optional multi-host deployment. Do not expose these services to an untrusted network without authentication and access controls.
