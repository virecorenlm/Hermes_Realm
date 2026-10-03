# AGENT_CHRONICLE.md — Public-Safe Chronicle Template

This is a generic replacement for the private Vire chronicle.

A chronicle is a human-readable continuity record for a local Hermes-based agent. It can include:

- system origin notes,
- major rebuilds,
- architecture decisions,
- hardware changes,
- memory migrations,
- failures and recovery notes,
- safety boundaries,
- future roadmap.

Do **not** commit private memories, family details, secrets, raw chat exports, or sensitive infrastructure data to a public chronicle.

---

## Suggested Structure

### Origin

Describe why this agent exists and what problem it solves.

### Hardware / Runtime

Start with one computer. If you add remote services, list functional roles and keep actual addresses in private configuration.

### Memory Architecture

Describe Redis/Qdrant/ChromaDB/SQLite/markdown roles.

### Voice Architecture

Describe wake/listen/transcribe/reason/speak flow.

### Operational Milestones

Keep a dated log of major implementation events.

### Known Gaps

Document what is not built yet.

### Safety Notes

Record rules for secrets, command execution, backups, and rollback.
