# Recovery notes

- Keep a copy of local identity and application state under your configured `HERMES_REALM_HOME` before changing the runtime.
- Back up Hermes state according to upstream Hermes guidance; `~/.hermes` belongs to Hermes and is not a Realm configuration directory.
- For Qdrant, use collection snapshots. Restore to a local or explicitly configured `QDRANT_URL` after verifying dimensions and collection names.
- Redis and hardware-specific service overrides are optional. Apply distribution-specific fixes only after reproducing the issue on your machine.
