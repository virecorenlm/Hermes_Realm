#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import urlopen
from urllib.parse import urlparse
BASE = Path(__file__).resolve().parent
AGENTS = ["network", "n8n", "content", "shopify", "seo", "crm", "email", "sheets", "hailo"]
PARKED_AGENTS = {x.strip().lower() for x in os.getenv("VIRE_WORKFORCE_PARKED_AGENTS", "shopify").split(",") if x.strip()}
@dataclass(frozen=True)
class Service:
    name: str; host: str; port: int; url: str | None = None
def configured_service(name, env_name, default, probe):
    url = os.getenv(env_name, default).rstrip('/')
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(f'{env_name} must be a URL with a hostname')
    return Service(name, parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), url + probe if probe is not None else None)

SERVICES = [
    configured_service('Ollama', 'OLLAMA_URL', 'http://127.0.0.1:11434', '/api/tags'),
    configured_service('n8n', 'N8N_URL', 'http://127.0.0.1:5678', ''),
    configured_service('Qdrant', 'QDRANT_URL', 'http://127.0.0.1:6333', '/collections'),
]
if os.getenv('DASHBOARD_URL'):
    SERVICES.append(configured_service('Realm Dashboard', 'DASHBOARD_URL', '', '/healthz'))
if os.getenv('CHROMA_URL'):
    SERVICES.append(configured_service('Chroma', 'CHROMA_URL', '', '/api/v2/heartbeat'))
if os.getenv('POSTGRES_URL'):
    SERVICES.append(configured_service('Postgres', 'POSTGRES_URL', '', None))
def now_stamp(): return datetime.now().strftime("%Y-%m-%d_%H%M%S")
def ensure_layout():
    for d in ["agents","memory","reports","logs","inbox","outbox","data"]: (BASE/d).mkdir(parents=True, exist_ok=True)
    for agent in AGENTS:
        root=BASE/'agents'/agent
        for d in ["inbox","outbox","data","processed"]: (root/d).mkdir(parents=True, exist_ok=True)
        mem=root/'memory.md'
        if not mem.exists():
            mem.write_text(f"# {agent.title()} Agent Memory\n\nCreated by Hermes Realm Workforce.\n", encoding='utf-8')
    state=BASE/'memory'/'business_state.md'
    if not state.exists():
        state.write_text("# Workforce Business State\n\n- Shopify is parked by default until the operator explicitly enables it.\n- Deterministic agents run from inbox/outbox files.\n", encoding='utf-8')
def read_json_or_text(path: Path) -> dict[str, Any]:
    text=path.read_text(encoding='utf-8', errors='replace')
    if path.suffix.lower()=='.json':
        try:
            data=json.loads(text); return data if isinstance(data, dict) else {'task': str(data), 'payload': data}
        except json.JSONDecodeError: return {'task': text.strip(), 'payload': {'parse_error': True}}
    return {'task': text.strip(), 'payload': {'source_format': path.suffix.lstrip('.') or 'text'}}
def write_json(path: Path, data: dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
def tcp_open(host, port, timeout=2.0):
    try:
        with socket.create_connection((host,port), timeout=timeout): return True
    except OSError: return False
def http_status(url, timeout=4.0):
    try:
        with urlopen(url, timeout=timeout) as resp: return f"HTTP {resp.status}"
    except URLError as exc: return f"ERR {exc.reason}"
    except Exception as exc: return f"ERR {type(exc).__name__}: {exc}"
def service_checks():
    if os.getenv("VIRE_WORKFORCE_SKIP_NETWORK"):
        return [{'name':svc.name,'endpoint':f'{svc.host}:{svc.port}','tcp':'SKIPPED','http':'skipped'} for svc in SERVICES]
    rows=[]
    for svc in SERVICES:
        tcp=tcp_open(svc.host,svc.port)
        rows.append({'name':svc.name,'endpoint':f'{svc.host}:{svc.port}','tcp':'UP' if tcp else 'DOWN','http':http_status(svc.url) if svc.url else 'n/a'})
    return rows
def list_files(path: Path):
    return sorted([p for p in path.iterdir() if p.is_file() and p.name!='.gitkeep']) if path.exists() else []
def latest_summary(path: Path, limit=260):
    files=list_files(path)
    if not files: return 'none'
    latest=max(files,key=lambda p:p.stat().st_mtime); text=' '.join(latest.read_text(encoding='utf-8', errors='replace').split())
    return f'{latest.name}: {text[:limit]}'
def agent_status(agent):
    root=BASE/'agents'/agent
    return {'agent':agent,'parked':agent in PARKED_AGENTS,'inbox':len(list_files(root/'inbox')),'outbox':len(list_files(root/'outbox')),'latest_outbox':latest_summary(root/'outbox')}
def append_log(name,line):
    ensure_layout(); ts=datetime.now().isoformat(timespec='seconds')
    with (BASE/'logs'/f'{name}.log').open('a',encoding='utf-8') as f: f.write(f'[{ts}] {line}\n')
def move_processed(path: Path, agent):
    processed=BASE/'agents'/agent/'processed'/f'{now_stamp()}_{path.name}'; processed.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(path), processed); return processed
# --- Shared agent boilerplate -------------------------------------------------
# Every *_agent.py defines AGENT, PURPOSE, and build_result(task, payload) -> dict,
# then delegates to agent_main(). All agents run in safe_mode: read-only/draft/plan.
def base_result(agent: str, purpose: str, task: str, payload: dict) -> dict[str, Any]:
    return {'agent':agent,'timestamp':datetime.now().isoformat(timespec='seconds'),'task':task,'purpose':purpose,'status':'complete','safe_mode':True,'actions':[],'findings':[],'next_steps':[],'data':{'payload':payload}}
def render_markdown(result):
    agent=str(result.get('agent','agent'))
    lines=[f"# {agent.title()} Agent Result","",f"**Generated:** {result['timestamp']}",f"**Task:** {result['task']}",f"**Status:** {result['status']}",f"**Safe mode:** {result['safe_mode']}","","## Actions"]
    lines += [f"- {x}" for x in result.get('actions', [])] or ['- none']
    lines += ["","## Findings"] + ([f"- {x}" for x in result.get('findings', [])] or ['- none'])
    lines += ["","## Next Steps"] + ([f"- {x}" for x in result.get('next_steps', [])] or ['- none'])
    if result.get('data'): lines += ["","## Data","","```json",json.dumps(result['data'], indent=2, sort_keys=True),"```"]
    return '\n'.join(lines)+'\n'
def process_inbox(agent: str, build_result: Callable[[str, dict], dict]):
    ensure_layout(); root=BASE/'agents'/agent; count=0
    for item in list_files(root/'inbox'):
        data=read_json_or_text(item); task=str(data.get('task') or data.get('title') or item.stem).strip(); payload=data.get('payload') if isinstance(data.get('payload'),dict) else {'raw_payload':data.get('payload')}
        result=build_result(task,payload or {}); stamp=now_stamp()
        out_md=root/'outbox'/f'{agent}_{stamp}_{item.stem}.md'; out_json=root/'data'/f'{agent}_{stamp}_{item.stem}.json'
        out_md.write_text(render_markdown(result), encoding='utf-8'); write_json(out_json,result); processed=move_processed(item,agent); append_log(agent,f'processed {item.name} -> {out_md.name}; archived {processed.name}'); count+=1
    if count==0: append_log(agent,'tick: no inbox items')
    print(f'{agent} processed={count}'); return count
def agent_main(agent: str, purpose: str, build_result: Callable[[str, dict], dict]):
    p=argparse.ArgumentParser(description=purpose); p.add_argument('--tick', action='store_true'); p.add_argument('--status', action='store_true'); args=p.parse_args()
    if args.status:
        ensure_layout(); root=BASE/'agents'/agent
        print(json.dumps({'agent':agent,'purpose':purpose,'parked':agent in PARKED_AGENTS,'inbox':len(list_files(root/'inbox')),'outbox':len(list_files(root/'outbox'))}, indent=2)); return 0
    process_inbox(agent,build_result); return 0
