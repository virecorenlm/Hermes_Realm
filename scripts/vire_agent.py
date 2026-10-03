#!/usr/bin/env python3
"""
vire_agent.py - local trusted task queue
Watches the configured Realm task queue for JSON task files.
Task types: bash, ollama, remember, http, plan

Run: python3 scripts/vire_agent.py
"""
import os, json, time, uuid, subprocess, requests, re
from pathlib import Path
from datetime import datetime, timezone
from realm_config import OLLAMA_URL, QDRANT_URL, realm_path

QUEUE_DIR   = realm_path("tasks", "queue")
DONE_DIR    = realm_path("tasks", "done")
FAILED_DIR  = realm_path("tasks", "failed")
PENDING_DIR = realm_path("tasks", "pending")
LOG_FILE    = realm_path("logs", "agent.log")

EMBED_URL   = OLLAMA_URL + "/api/embed"
COLLECTION  = "vire_memory"
POLL_SECS   = 5

PLANNER_SYSTEM = (
    "You are a local planning module. Given a goal, output a JSON array of task objects. "
    "Each: {\"type\":\"bash|ollama|remember|http\",\"payload\":{...},\"description\":\"...\"}. "
    "Output ONLY valid JSON array, no commentary."
)


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def embed(text):
    try:
        r = requests.post(EMBED_URL, json={"model": "qwen3-embedding", "input": text}, timeout=45)
        r.raise_for_status()
        return r.json()["embeddings"][0]
    except Exception as e:
        log(f"embed failed: {e}", "WARN")
        return None


def store_memory(content, category="general", tags=None):
    vec = embed(content)
    if not vec:
        return False
    try:
        response = requests.put(
            f"{QDRANT_URL}/collections/{COLLECTION}/points",
            json={"points": [{"id": str(uuid.uuid4()), "vector": vec, "payload": {
                "content": content, "category": category,
                "tags": tags or [], "stored_at": datetime.now(timezone.utc).isoformat(),
                "source": "vire_agent"
            }}]}, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        log(f"qdrant store failed: {e}", "WARN")
        return False


def run_bash(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"stdout": r.stdout.strip(), "stderr": r.stderr.strip(), "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "timeout", "returncode": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1}


def run_ollama(prompt, system="", model="qwen2.5-coder:3b", max_tokens=500):
    """Use ollama CLI via subprocess — avoids HTTP quirks from systemd context."""
    try:
        full_prompt = prompt
        if system:
            full_prompt = system + "\n\nUser: " + prompt
        for host in [OLLAMA_URL]:
            env = {**os.environ, "OLLAMA_HOST": host}
            result = subprocess.run(
                ["ollama", "run", model, full_prompt],
                capture_output=True, text=True, timeout=120, env=env
            )
            if result.returncode == 0 and result.stdout.strip():
                reply = result.stdout.strip()
                return re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
        return "ERROR: no ollama host responded"
    except Exception as e:
        return f"ERROR: {e}"


def run_http(method, url, payload=None, headers=None):
    try:
        fn = getattr(requests, method.lower())
        kwargs = {"timeout": 30}
        if payload:
            kwargs["json"] = payload
        if headers:
            kwargs["headers"] = headers
        r = fn(url, **kwargs)
        try:
            body = r.json()
        except Exception:
            body = r.text[:500]
        return {"status": r.status_code, "body": body}
    except Exception as e:
        return {"status": -1, "body": str(e)}


def expand_plan(goal):
    raw = run_ollama(f"Goal: {goal}", system=PLANNER_SYSTEM, max_tokens=600)
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return []
    try:
        steps = json.loads(m.group())
        return steps if isinstance(steps, list) else []
    except Exception:
        return []


def execute_task(task):
    t = task.get("type", "")
    p = task.get("payload", {})
    result = {"ok": False, "output": ""}

    if t == "bash":
        if os.environ.get("REALM_ALLOW_SHELL_TASKS") != "1":
            return {"ok": False, "output": "shell tasks disabled; set REALM_ALLOW_SHELL_TASKS=1 for a trusted queue"}
        out = run_bash(p.get("cmd", "echo no cmd"), p.get("timeout", 60))
        result["ok"] = out["returncode"] == 0
        result["output"] = out["stdout"] or out["stderr"]

    elif t == "ollama":
        out = run_ollama(p.get("prompt", ""), p.get("system", ""),
                         p.get("model", "qwen2.5-coder:3b"), p.get("max_tokens", 500))
        result["ok"] = not out.startswith("ERROR:")
        result["output"] = out

    elif t == "remember":
        ok = store_memory(p.get("content", ""), p.get("category", "general"), p.get("tags", []))
        result["ok"] = ok
        result["output"] = "stored" if ok else "failed"

    elif t == "http":
        if os.environ.get("REALM_ALLOW_HTTP_TASKS") != "1":
            return {"ok": False, "output": "HTTP tasks disabled; set REALM_ALLOW_HTTP_TASKS=1 for a trusted queue"}
        out = run_http(p.get("method", "GET"), p.get("url", ""), p.get("json"), p.get("headers"))
        result["ok"] = 200 <= out["status"] < 300
        result["output"] = str(out["body"])[:500]

    elif t == "plan":
        steps = expand_plan(p.get("goal", ""))
        if steps:
            for step in steps:
                step_id = str(uuid.uuid4())
                step["id"] = step_id
                (PENDING_DIR / f"{step_id}.json").write_text(json.dumps(step, indent=2))
            result["ok"] = True
            result["output"] = f"planned {len(steps)} steps for operator review in {PENDING_DIR}"
        else:
            result["output"] = "planning failed"

    else:
        result["output"] = f"unknown type: {t}"

    return result


def process_file(task_path):
    try:
        task = json.loads(task_path.read_text())
    except Exception as e:
        log(f"bad task {task_path.name}: {e}", "ERROR")
        task_path.rename(FAILED_DIR / task_path.name)
        return

    task_id = task.get("id", task_path.stem)
    task_type = task.get("type", "?")
    desc = task.get("description", str(task.get("payload", {}))[:60])
    log(f"running [{task_type}] {task_id[:8]}: {desc}")

    result = execute_task(task)
    status = "ok" if result["ok"] else "failed"
    out_preview = result["output"][:120]
    log(f"  -> {status}: {out_preview}")

    task["result"] = result
    task["completed_at"] = datetime.now(timezone.utc).isoformat()
    dest = DONE_DIR if result["ok"] else FAILED_DIR
    (dest / task_path.name).write_text(json.dumps(task, indent=2))
    task_path.unlink()

    if result["ok"] and result["output"] and task_type not in ("remember",):
        out_snippet = result["output"][:200]
        store_memory(
            f"[agent:{task_type}] {desc} -> {out_snippet}",
            category="session", tags=["agent", task_type]
        )


def main():
    for d in [QUEUE_DIR, DONE_DIR, FAILED_DIR, PENDING_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    log(f"=== VIRE AGENT started, polling {QUEUE_DIR} ===")
    while True:
        for tf in sorted(QUEUE_DIR.glob("*.json")):
            process_file(tf)
        time.sleep(POLL_SECS)


if __name__ == "__main__":
    main()
