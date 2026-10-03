#!/usr/bin/env python3
from __future__ import annotations
from common import agent_main, base_result
AGENT = "seo"
PURPOSE = "local keyword and on-page SEO planning (no crawls or external requests)"
def build_result(task: str, payload: dict) -> dict:
    result=base_result(AGENT, PURPOSE, task, payload)
    checklist=['Title tags carry a local keyword (e.g. "bait shop near <town>")','Meta descriptions are unique per page and under 160 chars','Product/hero images have descriptive alt text','Google Business profile hours and phone match the site','Pages load acceptably on mobile data']
    result['actions'].append('Generated an on-page SEO checklist locally; no crawls or external requests were made.')
    result['findings'].append('Checklist is generic until page-level notes are supplied in the task payload.')
    result['next_steps'].append('Walk the checklist against the live site manually and record gaps in the next task payload.')
    result['data']['seo_checklist']=checklist
    return result
if __name__ == '__main__': raise SystemExit(agent_main(AGENT, PURPOSE, build_result))
