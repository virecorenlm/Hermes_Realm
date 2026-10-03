#!/usr/bin/env python3
from __future__ import annotations
from common import agent_main, base_result
AGENT = "shopify"
PURPOSE = "offline Shopify relaunch/import prep (plan only; lane parked by default)"
def build_result(task: str, payload: dict) -> dict:
    result=base_result(AGENT, PURPOSE, task, payload)
    checklist=['Audit the product/category list offline against the shop floor','Prepare CSV import sheets locally','Verify pricing and inventory counts before any upload','Get explicit operator approval before any live store mutation']
    result['actions'].append('Planned Shopify work offline; no store API calls were made.')
    result['findings'].append('Shopify lane is parked by default (VIRE_WORKFORCE_PARKED_AGENTS); every run is plan-only.')
    result['next_steps'] += checklist
    result['data']['plan_checklist']=checklist
    return result
if __name__ == '__main__': raise SystemExit(agent_main(AGENT, PURPOSE, build_result))
