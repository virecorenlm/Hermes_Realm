#!/usr/bin/env python3
"""Queen orchestrator for the Hermes Realm workforce.

Commands: init, status, seed, tick-all, synthesize, dispatch, run-agent.
Dispatch writes task JSON into agents/<name>/inbox/; agents run as
subprocesses (<agent>_agent.py --tick) from this directory. Parked agents
(VIRE_WORKFORCE_PARKED_AGENTS, default: shopify) are never ticked.
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from datetime import datetime
from common import AGENTS, BASE, PARKED_AGENTS, agent_status, append_log, ensure_layout, latest_summary, list_files, now_stamp, service_checks, write_json

SEED_TASKS = {
    'network': 'Run read-only LAN service health scan',
    'n8n': 'Check n8n reachability and plan a read-only workflow inventory',
    'content': 'Draft one bait shop content outline',
    'shopify': 'Plan offline Shopify catalog review (plan only)',
    'seo': 'Generate the on-page SEO checklist for the shop site',
    'crm': 'Draft the weekly follow-up plan (draft only)',
    'email': 'Draft the weekly status email (draft only, never send)',
    'sheets': 'Prepare KPI reporting columns',
    'hailo': 'Inventory local Hailo HEF models',
}

def _require_agent(agent):
    if agent not in AGENTS: raise SystemExit(f"unknown agent: {agent} (choose from: {', '.join(AGENTS)})")

def slug(text, limit=40):
    return re.sub(r'[^a-z0-9]+','-',text.lower()).strip('-')[:limit] or 'task'

def dispatch(agent, task, priority='normal', payload=None):
    _require_agent(agent); ensure_layout()
    data={'task':task,'priority':priority,'payload':payload or {},'dispatched_at':datetime.now().isoformat(timespec='seconds'),'source':'queen'}
    path=BASE/'agents'/agent/'inbox'/f'{now_stamp()}_{slug(task)}.json'
    write_json(path,data); append_log('queen',f'dispatched to {agent}: {task}')
    if agent in PARKED_AGENTS: print(f'note: {agent} is parked; task queued but tick-all will skip it')
    print(f'dispatched -> {path.relative_to(BASE)}'); return path

def run_agent(agent):
    _require_agent(agent); ensure_layout()
    if agent in PARKED_AGENTS:
        print(f'{agent} is parked (VIRE_WORKFORCE_PARKED_AGENTS); refusing to tick it. Un-park explicitly to run it.'); return 1
    proc=subprocess.run([sys.executable,str(BASE/f'{agent}_agent.py'),'--tick'],cwd=BASE,capture_output=True,text=True,timeout=180)
    if proc.stdout.strip(): print(proc.stdout.strip())
    if proc.returncode!=0 and proc.stderr.strip(): print(proc.stderr.strip(),file=sys.stderr)
    append_log('queen',f'ran {agent} rc={proc.returncode}')
    return proc.returncode

def tick_all():
    ensure_layout(); failed=[]
    for agent in AGENTS:
        if agent in PARKED_AGENTS: print(f'{agent}: parked, skipped'); continue
        if run_agent(agent)!=0: failed.append(agent)
    if failed: print(f"tick-all failures: {', '.join(failed)}",file=sys.stderr); return 1
    print('tick-all complete'); return 0

def seed():
    ensure_layout(); count=0
    for agent in AGENTS:
        if agent in PARKED_AGENTS: print(f'{agent}: parked, not seeded'); continue
        dispatch(agent,SEED_TASKS[agent],priority='normal'); count+=1
    print(f'seeded {count} agents'); return 0

def render_status():
    ensure_layout()
    lines=['# Workforce Status','',f"**Generated:** {datetime.now().isoformat(timespec='seconds')}",f"**Parked agents:** {', '.join(sorted(PARKED_AGENTS)) or 'none'}",'','## Services','','| service | endpoint | tcp | http |','|---|---|---|---|']
    lines += [f"| {r['name']} | {r['endpoint']} | {r['tcp']} | {r['http']} |" for r in service_checks()]
    lines += ['','## Agents','','| agent | parked | inbox | outbox |','|---|---|---|---|']
    rows=[agent_status(a) for a in AGENTS]
    lines += [f"| {r['agent']} | {'yes' if r['parked'] else 'no'} | {r['inbox']} | {r['outbox']} |" for r in rows]
    lines += ['','## Latest Outbox','']
    lines += [f"- **{r['agent']}**: {r['latest_outbox']}" for r in rows]
    report='\n'.join(lines)+'\n'
    path=BASE/'reports'/f'status_{now_stamp()}.md'; path.write_text(report,encoding='utf-8')
    append_log('queen',f'status report -> {path.name}')
    return report, path

def synthesize():
    ensure_layout()
    lines=['# Workforce Synthesis','',f"**Generated:** {datetime.now().isoformat(timespec='seconds')}",'']
    for agent in AGENTS:
        outbox=BASE/'agents'/agent/'outbox'
        lines += [f'## {agent.title()}','',f'- Outbox items: {len(list_files(outbox))}',f'- Latest: {latest_summary(outbox)}','']
    report='\n'.join(lines)+'\n'
    path=BASE/'reports'/f'synthesis_{now_stamp()}.md'; path.write_text(report,encoding='utf-8')
    append_log('queen',f'synthesis report -> {path.name}')
    print(f'synthesis -> {path.relative_to(BASE)}'); return 0

def main():
    p=argparse.ArgumentParser(description='Queen orchestrator for the Hermes Realm workforce')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init',help='create the workforce directory layout')
    sub.add_parser('status',help='safe read-only service+agent report -> reports/')
    sub.add_parser('seed',help='dispatch starter tasks into non-parked agent inboxes')
    sub.add_parser('tick-all',help='run every non-parked agent once')
    sub.add_parser('synthesize',help='roll up agent outboxes -> reports/')
    d=sub.add_parser('dispatch',help='write a task JSON into an agent inbox')
    d.add_argument('agent'); d.add_argument('task'); d.add_argument('--priority',default='normal'); d.add_argument('--payload',default='{}',help='JSON object string')
    r=sub.add_parser('run-agent',help='tick a single non-parked agent')
    r.add_argument('agent')
    args=p.parse_args()
    if args.command=='init': ensure_layout(); print(f'layout ready under {BASE}'); return 0
    if args.command=='status':
        report,path=render_status(); print(report); print(f'status -> {path.relative_to(BASE)}'); return 0
    if args.command=='seed': return seed()
    if args.command=='tick-all': return tick_all()
    if args.command=='synthesize': return synthesize()
    if args.command=='dispatch':
        try:
            payload=json.loads(args.payload)
        except json.JSONDecodeError as exc: raise SystemExit(f'--payload must be valid JSON: {exc}')
        if not isinstance(payload,dict): raise SystemExit('--payload must be a JSON object')
        dispatch(args.agent,args.task,args.priority,payload); return 0
    if args.command=='run-agent': return run_agent(args.agent)
    return 2

if __name__ == '__main__': raise SystemExit(main())
