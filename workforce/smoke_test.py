#!/usr/bin/env python3
"""Offline smoke test for the workforce fleet.

Copies the workforce *.py files into a temp directory and drives the full
loop there, so the real workforce/ tree is never touched and no network
probes run (VIRE_WORKFORCE_SKIP_NETWORK=1). Stdlib only; exits 0 on pass.

Proves: py_compile passes, init creates the layout, seed writes inbox
tasks, tick-all processes them, synthesize + status write reports, and
workforce_status.py runs without crashing.
"""
from __future__ import annotations
import os, py_compile, shutil, subprocess, sys, tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
from common import AGENTS, PARKED_AGENTS  # noqa: E402

CHECKS = []

def check(name, ok, detail=''):
    CHECKS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f' — {detail}' if detail and not ok else ''))

def run(args, cwd, env):
    proc = subprocess.run([sys.executable, *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
    return proc.returncode, (proc.stdout + proc.stderr).strip()

def main():
    for path in sorted(SRC.glob('*.py')):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            check(f'py_compile {path.name}', False, str(exc)); break
    else:
        check('py_compile workforce/*.py', True)

    tmp = Path(tempfile.mkdtemp(prefix='workforce_smoke_'))
    try:
        for path in SRC.glob('*.py'): shutil.copy2(path, tmp / path.name)
        env = {**os.environ, 'VIRE_WORKFORCE_SKIP_NETWORK': '1'}
        env.pop('VIRE_WORKFORCE_PARKED_AGENTS', None)  # test the default parked set
        queen = ['queen_orchestrator.py']
        active = [a for a in AGENTS if a not in PARKED_AGENTS]

        rc, out = run(queen + ['init'], tmp, env)
        layout_ok = all((tmp/'agents'/a/d).is_dir() for a in AGENTS for d in ['inbox','outbox','data','processed'])
        check('init creates agent folders', rc == 0 and layout_ok, out)

        rc, out = run(queen + ['seed'], tmp, env)
        seeded = all(list((tmp/'agents'/a/'inbox').glob('*.json')) for a in active)
        parked_empty = not list((tmp/'agents'/'shopify'/'inbox').glob('*.json'))
        check('seed writes inbox tasks (parked skipped)', rc == 0 and seeded and parked_empty, out)

        rc, out = run(queen + ['dispatch', 'network', 'Smoke scan', '--priority', 'high', '--payload', '{"reason":"smoke"}'], tmp, env)
        check('dispatch writes a task', rc == 0 and len(list((tmp/'agents'/'network'/'inbox').glob('*.json'))) == 2, out)

        rc, out = run(queen + ['tick-all'], tmp, env)
        drained = all(not list((tmp/'agents'/a/'inbox').glob('*.json')) for a in active)
        produced = all(list((tmp/'agents'/a/'outbox').glob('*.md')) and list((tmp/'agents'/a/'processed').iterdir()) for a in active)
        check('tick-all processes tasks', rc == 0 and drained and produced, out)

        rc, out = run(queen + ['run-agent', 'shopify'], tmp, env)
        check('run-agent refuses parked agent', rc != 0, out)

        rc, out = run(queen + ['synthesize'], tmp, env)
        check('synthesize creates a report', rc == 0 and bool(list((tmp/'reports').glob('synthesis_*.md'))), out)

        rc, out = run(queen + ['status'], tmp, env)
        check('status creates a report', rc == 0 and bool(list((tmp/'reports').glob('status_*.md'))), out)

        rc, out = run(['workforce_status.py'], tmp, env)
        check('workforce_status.py runs', rc == 0 and 'Workforce Status' in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [name for name, ok in CHECKS if not ok]
    print(f'\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed')
    return 1 if failed else 0

if __name__ == '__main__': raise SystemExit(main())
