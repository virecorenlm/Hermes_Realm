---
name: vire-consciousness-pulse
description: "Use when reviewing or adapting optional scheduled status and reflection scripts."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [cron, pulse, status, safety]
---

# Scheduled pulse experiments

`cron-pulses/` contains one-shot scripts for local state observations, Qdrant checks, and optional logs. They are not scheduled by this repository. Review each script's dependencies, file writes, camera/audio behavior, and service URLs before adding a cron entry. Use `HERMES_REALM_HOME` for Realm state and `QDRANT_URL` for optional vector-memory checks.

Keep scheduled actions local and bounded. External messages, account changes, destructive operations, and spending require separate operator authorization. Record observations accurately and do not infer a running service from a configured URL.
