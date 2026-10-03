# Hermes Realm Workforce

Working deterministic workforce implementation for this repository.

## Quick start

```bash
cd workforce
python3 queen_orchestrator.py init
python3 queen_orchestrator.py status
python3 queen_orchestrator.py seed
python3 queen_orchestrator.py tick-all
python3 queen_orchestrator.py synthesize
```

## Safety model

- File-backed inbox/outbox agents; no database required.
- Stdlib-only Python; no pip install required.
- Shopify is parked by default via `VIRE_WORKFORCE_PARKED_AGENTS=shopify`.
- Email/CRM agents draft and plan only; they do not send messages.
- Network/n8n status checks are read-only reachability probes.

## Agents

- `network`: fleet/service reachability scan
- `n8n`: n8n health and read-only workflow inventory planning
- `content`: fishing/social content hooks and calendars
- `shopify`: offline relaunch/import prep only while parked
- `seo`: local keyword planning
- `crm`: follow-up structure/drafts only
- `email`: triage/draft policy only
- `sheets`: KPI/reporting schema
- `hailo`: local HEF inventory and vision planning

Each agent uses `agents/<name>/inbox`, `outbox`, `data`, and `processed`.
