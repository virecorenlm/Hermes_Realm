#!/usr/bin/env python3
from __future__ import annotations
from common import agent_main, base_result, service_checks
AGENT = "network"
PURPOSE = "read-only fleet/service reachability scan"
def build_result(task: str, payload: dict) -> dict:
    result=base_result(AGENT, PURPOSE, task, payload)
    rows=service_checks()
    up=[r for r in rows if r['tcp']=='UP']; down=[r for r in rows if r['tcp']=='DOWN']; skipped=[r for r in rows if r['tcp']=='SKIPPED']
    result['actions'].append('Probed LAN services read-only (TCP connect + HTTP GET); no configuration was changed.')
    if skipped:
        result['findings'].append(f'Network probes skipped for {len(skipped)} services (VIRE_WORKFORCE_SKIP_NETWORK set).')
    else:
        result['findings'].append(f'{len(up)}/{len(rows)} services reachable over TCP.')
        result['findings'] += [f"DOWN: {r['name']} ({r['endpoint']})" for r in down]
    result['next_steps'].append('Investigate DOWN services from their host console before restarting anything.')
    result['data']['services']=rows
    return result
if __name__ == '__main__': raise SystemExit(agent_main(AGENT, PURPOSE, build_result))
