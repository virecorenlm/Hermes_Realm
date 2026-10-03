---
name: realm-state-graph-operator
description: "Use when prioritizing findings from a local Realm state graph without modifying sources."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# State graph operator pattern

Consume a graph report, verify each referenced path or service, and rank missing dependencies, stale references, and safety issues. Emit a bounded report with evidence and suggested next steps. Do not repair automatically. Graph generation and operator scripts are optional companion projects and are not part of this checkout.
