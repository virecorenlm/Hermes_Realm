---
name: vire-file-management
description: "Use when organizing Realm files, protecting secrets, and preserving duplicate-looking content."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [filesystem, pi5, organization, secrets, cleanup]
    related_skills: [vire]
---

# Vire — File System Access & Management

## Portable file layout

When organizing the configured Realm directory, preserve compatibility and traceability. Keep manifests for renames and never infer duplicates from filenames alone.

Critical rules:
- Do not move hidden runtime/config directories like `.hermes`, `.openclaw`, `.ollama`, `.vire`, `.ssh`, `.config`, or `.local` during cleanup passes unless the operator explicitly asks.
- Leave standard XDG desktop folders (`Desktop`, `Documents`, `Downloads`, `Music`, `Pictures`, `Public`, `Templates`, `Videos`) in place unless there is a specific reason to change them.
- Keep existing application paths stable or update callers when reorganizing files.
- Never delete, merge, or overwrite duplicate-looking notes such as `shared_text.txt` / `shared_text (2).txt`; use meaningful slugs plus short content hashes and write old-path → new-path manifests.

## Core Paths
```
~/.config/hermes-realm/                    — Vire's home base
~/.config/hermes-realm/content/            — Generated content staging
~/.config/hermes-realm/content/video/      — Raw and edited video
~/.config/hermes-realm/content/images/     — Graphics and thumbnails
~/.config/hermes-realm/content/scheduled/  — Queued posts
~/.config/hermes-realm/logs/               — All operation logs
~/.config/hermes-realm/secrets/           — API credentials (chmod 600)
```

## File Permissions — Secrets
```bash
chmod 700 ~/.config/hermes-realm/secrets/
chmod 600 ~/.config/hermes-realm/secrets/*.env
chmod 600 ~/.config/hermes-realm/secrets/*.json
```

## Log All Operations
```bash
# Append to daily log
echo "[$(date -Iseconds)] $ACTION" >> ~/.config/hermes-realm/logs/$(date +%Y-%m-%d).log
```

## Clean Old Content

Inventory candidates and confirm exact paths with the operator before removing any content.

## Guardrails

- Never delete files in `~/.config/hermes-realm/content/` without confirming with owner.
- All destructive operations require explicit confirmation from owner.
