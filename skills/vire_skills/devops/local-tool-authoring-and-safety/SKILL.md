---
name: local-tool-authoring-and-safety
description: "Use when adding, testing, exposing, or debugging local tools for Vire/Hermes/Tool Router/MCP-style runtimes; emphasizes parameter validation, secrets handling, manual curl verification, sandboxing, and safe side-effect boundaries."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [tools, tool-router, mcp, safety, api, validation, local-agent]
    related_skills: [qdrant-memory-agent-v2, realm-state-graph-operator, native-mcp, hermes-agent, anti-ai-slop-code-standards]
---

# Local Tool Authoring and Safety

Also known as: `mcp-tool-authoring-and-safety` from the Qdrant AI skill-mining report. The final installed name is broader because the same safety rules apply to Vire Tool Router tools, MCP servers, HTTP services, n8n webhooks, and Hermes-facing local actions.

## Trigger

Use this skill when creating or modifying local tools exposed to Vire/Hermes through Tool Router, MCP-style services, HTTP endpoints, n8n webhooks, or similar agent-action interfaces.

This skill exists because Qdrant skill mining found tool-authoring safety as the highest leverage next class of skill: Vire is increasingly able to act, so tools must be consistent, testable, and safely bounded.

## Core Principles

1. **Define the side-effect boundary first.** Mark whether the tool is read-only, writes local reports/state, edits files, controls services, or touches external APIs.
2. **Validate parameters before action.** Reject missing, unknown, or unsafe parameters with structured errors.
3. **Keep secrets out of code and reports.** Read credentials from env files or secret paths; never print full tokens.
4. **Manual test before agent use.** Every tool needs a direct curl/CLI test independent of the LLM.
5. **Return structured JSON.** Include `ok`, result fields, and actionable `error` messages.
6. **Log enough to debug, not enough to leak.** Log tool name, timestamp, parameter keys, status, and short errors; avoid raw secrets/payload dumps.
7. **Prefer dry-run or report-only mode for new side effects.** Graduate to write/action only after verification.
8. **Do not rebuild existing routers.** Patch the current Tool Router or MCP integration unless dedupe proves a new service is required.

## Safe Tool Creation Checklist

- [ ] Tool name is stable, verb-first, and specific enough to route.
- [ ] Description says what it does and what it will not do.
- [ ] JSON schema/properties list expected parameters.
- [ ] Required parameters are explicit.
- [ ] Side-effect level is documented.
- [ ] Dangerous paths/actions are allowlisted, not merely blocklisted.
- [ ] API keys/secrets are loaded from configured secret storage.
- [ ] Manual curl/CLI test succeeds.
- [ ] Failure mode was tested with bad/missing parameters.
- [ ] Tool appears in `/list_tools` or equivalent registry.
- [ ] Tool can be called through `/execute_tool` or equivalent endpoint.
- [ ] Result is recorded in a report/state file if it produces durable output.

## Vire Tool Router Authoring Recipe

When adding a tool to `${HERMES_REALM_HOME:-$HOME/.config/hermes-realm}/tools/vire_tool_router.py`:

1. Add a small `tool_<name>(params: dict[str, Any]) -> dict[str, Any]` function.
2. Validate required parameters at the top and return `{"ok": false, "error": "..."}` on bad input.
3. For shell commands, prefer fixed command lists over string interpolation.
4. If dynamic paths are allowed, restrict them to known safe roots.
5. Bound timeouts and stdout/stderr size.
6. Add artifacts to the result when the tool writes state/reports.
7. Register the tool with `register(...)`, including schema properties and `side_effects`.
8. Compile the router.
9. Restart `vire-tool-router.service`.
10. Verify with `/list_tools` and `/execute_tool`.

Minimal shape:

```python
def tool_example(params: dict[str, Any]) -> dict[str, Any]:
    required = params.get("required")
    if not required:
        return {"ok": False, "error": "missing required parameter: required"}
    return {"ok": True, "value": required}

register(
    "example",
    "Do one specific bounded thing.",
    tool_example,
    {"required": {"type": "string"}},
    required=["required"],
    side_effects="read",
)
```

Compile and restart:

```bash
python3 -m py_compile ${HERMES_REALM_HOME:-$HOME/.config/hermes-realm}/tools/vire_tool_router.py
systemctl --user restart vire-tool-router.service
```

## Manual Verification Pattern

List tools:

```bash
curl -s http://127.0.0.1:8791/list_tools | python3 -m json.tool
```

Execute a tool:

```bash
curl -s -X POST http://127.0.0.1:8791/execute_tool \
  -H 'Content-Type: application/json' \
  -d '{"tool":"router_status","parameters":{}}' | python3 -m json.tool
```

External/API-style tool smoke test pattern from the Qdrant source:

```bash
curl -s -X POST http://127.0.0.1:8791/execute_tool \
  -H 'Content-Type: application/json' \
  -d '{"tool":"your_tool","parameters":{"sample":"small_safe_value"}}' | python3 -m json.tool
```

For tools with side effects, first prefer a dry-run/report-only equivalent if implemented. If no dry-run exists, use the smallest safe scope and inspect returned artifacts.

## Good First Tool Categories

The Qdrant source listed broad MCP/API integrations. For Vire, prioritize by operational value and safety:

1. **Read-only status tools** — service health, disk, Qdrant collections, Redis keys, Ollama tags.
2. **Report-producing tools** — run scouts, graph operators, curators, source reassemblers.
3. **External read APIs** — weather, search, docs, package metadata, GitHub read endpoints.
4. **Local controlled writes** — write reports/state under `${HERMES_REALM_HOME:-$HOME/.config/hermes-realm}/reports` or `/state`.
5. **Human-visible sends/posts** — Telegram/social/email; require explicit target checks and careful previews.
6. **Service control/tools with real side effects** — restart services, file edits, deploys; require narrow allowlists and rollback notes.

Avoid building broad arbitrary command tools. If a tool can become “run anything,” it belongs behind stronger approval, not ordinary autonomous routing.

## Parameter Validation Pattern

A tool should return structured errors like:

```json
{"ok": false, "error": "missing required parameter: location"}
```

Avoid silent defaults for actions that affect files, services, external APIs, or user-visible messaging.

## Secrets Pattern

- Put credentials in secret files or environment variables.
- Check presence without printing values.
- In logs and reports, show only secret key names or redacted previews.
- Never commit credentials into skills, reports, source, or Qdrant-ingested examples.

## Tool Failure Debugging

1. Call the tool manually with curl/CLI.
2. Check router/service health.
3. Check logs for the tool name and parameter keys.
4. Test missing/bad parameters to confirm validation path.
5. If external API fails, separate credential failure, network failure, rate limit, and bad request.
6. If the tool writes files/reports, verify the artifact exists and can be read back.

## Qdrant Source Evidence

This skill was created from Qdrant skill mining on 2026-06-25. Primary source:

- `~/Desktop/MCP_TOOLS_GUIDE.md`
- Reassembled report: `${HERMES_REALM_HOME:-$HOME/.config/hermes-realm}/reports/qdrant_sources/MCP_TOOLS_GUIDE.md.md`
- Candidate report: `${HERMES_REALM_HOME:-$HOME/.config/hermes-realm}/reports/qdrant_skill_mining/ai_skill_build_candidates_latest.md`
- Condensed support notes: `references/qdrant-mcp-tools-guide-2026-06-25.md`

## Pitfalls

- Do not expose a shell-like arbitrary execution tool unless the environment and caller trust boundary is explicit.
- Do not let an LLM invent tool parameters; schema and validation own the contract.
- Do not treat a tool as verified just because it appears in the registry; call it and inspect output.
- Do not create a new router when the current Vire Tool Router can be patched.
