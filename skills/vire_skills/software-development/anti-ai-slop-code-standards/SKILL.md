---
name: anti-ai-slop-code-standards
description: "Use when writing or reviewing generated code for failure handling, bounded permissions, tests, and explainability."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Code quality gate

Generated code needs the same review as hand-written code. Passing once is insufficient evidence of reliability.

## Review sequence

1. State what the change does and where it reads or writes.
2. Identify inputs, permissions, external services, and failure modes.
3. Prefer explicit allowlists, local bind addresses, bounded timeouts, and least privilege.
4. Check errors and return values before reporting success.
5. Run relevant syntax checks and focused tests, then inspect the diff for unrelated changes.
6. Verify that logs, reports, and public files contain no credentials or personal data.
7. Explain remaining risks and configuration requirements to the operator.

## Common failures

- An endpoint reads arbitrary local paths supplied by a caller.
- A test server binds to all interfaces without authentication.
- A background task waits indefinitely on a model, subprocess, or network call.
- A log prints request bodies containing tokens or personal content.
- A script assumes a particular machine, directory, account, or service exists.
- A public export includes raw private memory or host inventory.

Use secret scanning as a supplement to manual review. Keep raw operational data outside public Git and publish only reviewed examples.
