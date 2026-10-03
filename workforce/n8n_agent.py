#!/usr/bin/env python3
from __future__ import annotations
from common import agent_main, base_result, service_checks
AGENT = "n8n"
PURPOSE = "n8n health check and read-only workflow inventory planning"
def build_result(task: str, payload: dict) -> dict:
    result=base_result(AGENT, PURPOSE, task, payload)
    rows=[r for r in service_checks() if 'n8n' in r['name'].lower()]
    result['actions'].append('Checked n8n reachability read-only; no workflows were created, modified, or executed.')
    if rows:
        result['findings'] += [f"{r['name']} ({r['endpoint']}): TCP {r['tcp']}, HTTP {r['http']}" for r in rows]
    else:
        result['findings'].append('No n8n service configured in SERVICES (common.py).')
    result['next_steps'].append('Inventory existing workflows via the n8n UI before scripting any automation against it.')
    result['data']['services']=rows
    return result
if __name__ == '__main__': raise SystemExit(agent_main(AGENT, PURPOSE, build_result))
