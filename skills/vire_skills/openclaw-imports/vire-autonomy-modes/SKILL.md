---
name: vire-autonomy-modes
description: "Use when setting operator-controlled permission boundaries for a local Hermes Realm agent."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Operator-controlled permissions

The operator defines scope for each task or deployment. A public installation carries no inherited autonomy grant.

| Level | Examples | Rule |
| --- | --- | --- |
| Read-only | Inspect local files, service health, and reports | Stay within configured paths and privacy policy |
| Local writes | Drafts, logs, queue files, and workspace code | Use approved paths and reversible changes |
| Destructive changes | Delete, overwrite, service reconfiguration | Confirm the exact action first |
| External accounts | Email, social posts, store mutations | Confirm account and action first |
| Spending | Purchases, subscriptions, paid APIs | Require explicit authorization every time |

Delegation of a task does not remove these boundaries. Record approvals and report outcomes. The queue runner disables shell and HTTP tasks by default; enabling them also requires a trusted local queue writer.
