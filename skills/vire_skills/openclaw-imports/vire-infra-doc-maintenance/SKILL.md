---
name: vire-infra-doc-maintenance
description: "Use when keeping service and hardware documentation aligned with an operator's deployment."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Infrastructure documentation maintenance

Treat `architecture.md` and `docs/NETWORK_SERVICES.md` as public examples. For each service, verify its URL, protocol, health endpoint, dependency, and whether it is actually installed. Record private addresses and machine inventories in operator-local documentation, not this repository. A single computer is the default; add remote hosts only when the operator configures them.

Distinguish observed runtime state from a plan. Prefer read-only checks before changing configuration. Follow the operator permission model in `vire-autonomy-modes` for any write or service restart.
