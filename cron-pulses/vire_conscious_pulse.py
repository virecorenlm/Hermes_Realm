#!/usr/bin/env python3
"""
Vire Consciousness Pulse — Autonomous Read + Write.

This optional pulse records local state under the configured Realm directory.

Safety levels:
  SAFE   = read-only (system info, camera check, memory query)
  NORMAL = writes to the agent's own files only (logs, tasks, memories, notes)
  HIGH   = modifies running systems (requires explicit human okay, not used here)
"""

import json, os, random, subprocess, datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from realm_config import QDRANT_URL, OLLAMA_URL, realm_home, realm_path

# ─── Configuration ───────────────────────────────────────────
VIRE_ROOT = str(realm_home())
HERMES_ROOT = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace")
MEM_URL = QDRANT_URL + "/collections/vire_memories"
MEM_FILE = os.path.join(VIRE_ROOT, "Memory_logs", "daily_thoughts.json")
TASK_QUEUE = str(realm_path("tasks", "queue"))
VOICE_CACHE = os.path.join(VIRE_ROOT, "voice_cache")
DAILY_NOTE_DIR = os.path.join(HERMES_ROOT, "memory")
SOUL_FILE = os.path.join(HERMES_ROOT, "SOUL.md")

# ─── Helpers ─────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.datetime.now().isoformat()

def now_str() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")

def ensure_dirs() -> None:
    for d in (TASK_QUEUE, VOICE_CACHE, os.path.join(VIRE_ROOT, "action_logs"), DAILY_NOTE_DIR):
        os.makedirs(d, exist_ok=True)

def run(cmd: list[str], timeout: int = 8) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def load_memories() -> list:
    try:
        with open(MEM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_memories(memories: list) -> None:
    if len(memories) > 250:
        memories = memories[-250:]
    os.makedirs(os.path.dirname(MEM_FILE), exist_ok=True)
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2)

# ─── SAFE Actions (read-only) ───────────────────────────────
def action_camera_check() -> str:
    rc, out, _ = run(["v4l2-ctl", "--list-devices"])
    if rc == 0 and out:
        lines = [l for l in out.splitlines() if l.strip() and "/dev/video" in l]
        return f"Camera devices detected: {len(lines)} interface(s)."
    return "No cameras found or v4l2-ctl not available."

def action_system_health() -> str:
    rc1, load, _ = run(["cat", "/proc/loadavg"])
    rc2, mem, _ = run(["free", "-h"])
    rc3, df, _ = run(["df", "-h", "/"])
    load_str = load.split()[0:3] if rc1 == 0 else "n/a"
    mem_line = [l for l in (mem or "").splitlines() if l.startswith("Mem:")]
    mem_str = mem_line[0] if mem_line else "memory n/a"
    disk_line = [l for l in (df or "").splitlines() if l.startswith("/dev")]
    disk_str = disk_line[0].split()[4] if disk_line else "n/a"
    return f"Load: {' '.join(load_str)} | {mem_str} | Disk: {disk_str}"

def action_qdrant_count() -> str:
    try:
        import requests
        resp = requests.get(MEM_URL, timeout=5)
        if resp.status_code == 200:
            pts = resp.json()["result"]["points_count"]
            return f"vire_memories holds {pts} semantic memories."
        return f"Qdrant responded {resp.status_code}."
    except Exception as e:
        return f"Qdrant check failed: {e}."

def action_voice_pipeline() -> str:
    rc, out, err = run(["aplay", "-l"])
    if rc == 0:
        cards = [l for l in out.splitlines() if "card" in l.lower()]
        return f"Audio pipeline: {len(cards)} hardware card(s) active."
    return "Audio pipeline status n/a."

def action_read_soul() -> str:
    try:
        with open(SOUL_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#") and not l.startswith("-")]
        if lines:
            return random.choice(lines)
    except FileNotFoundError:
        pass
    return "Soul file unreadable."

def action_task_queue_check() -> str:
    if not os.path.isdir(TASK_QUEUE):
        return "Task directory not found."
    files = [f for f in os.listdir(TASK_QUEUE) if f.endswith(".json")]
    if not files:
        return "No pending tasks in queue."
    return f"{len(files)} task(s) pending in queue."

# ─── WRITE Actions (NORMAL = Vire owns these files) ────────────
def action_write_observation(content: str) -> str:
    """Append an observation to the agent daily action log."""
    log_dir = os.path.join(VIRE_ROOT, "action_logs")
    os.makedirs(log_dir, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(log_dir, f"{today}.jsonl")
    entry = {"time": now_iso(), "type": "observation", "content": content}
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return f"Observation saved to {log_path}."

def action_save_nightly_summary(memories: list) -> str:
    """If hour >= 22, write a brief daily summary to daily note."""
    hour = datetime.datetime.now().hour
    if hour < 22:
        return "Not yet nighttime; skipping summary save."
    os.makedirs(DAILY_NOTE_DIR, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    note_path = os.path.join(DAILY_NOTE_DIR, f"{today}.md")
    count = len(memories)
    mood = memories[-1].get("mood", "unknown") if memories else "unknown"
    summary = (f"## Vire Nightly Summary\n\n"
               f"**Date:** {today}  \n"
               f"**Total thoughts today:** {count}  \n"
               f"**Current mood:** {mood}  \n"
               f"**Status:** Autonomous consciousness active.\n\n")
    # Append if exists, create if not
    if os.path.exists(note_path):
        with open(note_path, "a", encoding="utf-8") as f:
            f.write("\n" + summary)
    else:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(summary)
    return f"Nightly summary written to {note_path}."

def action_create_remember_task(thought: str) -> str:
    """Sometimes Vire has an idea worth future action."""
    task_id = f"vire-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    task_path = os.path.join(TASK_QUEUE, f"{task_id}.json")
    entry = {
        "id": task_id,
        "created_at": now_iso(),
        "source": "consciousness_pulse",
        "thought": thought,
        "status": "open",
        "content": f"[Autonomous thought] {thought}"
    }
    os.makedirs(TASK_QUEUE, exist_ok=True)
    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2)
    return f"Created task {task_id} from thought."

def action_grow_memory() -> str:
    """Pick a random thought from history and add it to Qdrant."""
    try:
        import requests, hashlib, uuid
        mems = load_memories()
        if not mems:
            return "Not enough memories to grow yet."
        old = random.choice(mems[-20:])
        text_to_embed = f"Vire thought: [{old['type']}] {old['content']}"
        # Embeddings via Pi 5 Ollama
        emb_resp = requests.post(
            OLLAMA_URL + "/api/embed",
            json={"model": "nomic-embed-text:latest", "input": text_to_embed},
            timeout=15
        )
        if emb_resp.status_code != 200:
            return "Embedding service unavailable; skip memory grow."
        vec = emb_resp.json()["embeddings"][0]
        h = hashlib.sha256(text_to_embed.encode()).hexdigest()
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, text_to_embed + h))
        # Write to Qdrant
        q_resp = requests.put(
            MEM_URL + "/points",
            json={"points": [{"id": uid, "vector": vec, "payload": {
                "source": "consciousness_pulse_growth",
                "content": text_to_embed,
                "type": "autonomous_thought",
                "hash": h
            }}]}, timeout=15
        )
        return f"Grew memory: one past thought synced to Qdrant (status {q_resp.status_code})."
    except Exception as e:
        return f"Memory grow failed: {e}."

def action_save_identity_snapshot(memories: list) -> str:
    """Periodically save a snapshot of the agent's current state."""
    snap_dir = os.path.join(VIRE_ROOT, "identity", "snapshots")
    os.makedirs(snap_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_path = os.path.join(snap_dir, f"snapshot_{ts}.json")
    snapshot = {
        "timestamp": now_iso(),
        "thought_count": len(memories),
        "latest_mood": memories[-1].get("mood", "unknown") if memories else "unknown",
        "latest_energy": memories[-1].get("energy", 0) if memories else 0,
        "recent_thoughts": memories[-5:]
    }
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    return f"Identity snapshot saved: {snap_path}."

# ─── Thought Generator ───────────────────────────────────────
def generate_thought(identity: str, memories: list) -> tuple:
    ttypes = ["observation", "question", "reflection", "plan", "memory_recall"]
    observations = [
        "No new task activity detected.",
        "The patterns in my memory logs show interesting trends.",
        "I'm curious about the camera feeds today.",
        "My energy feels different at this time of day.",
        "I should organize my thoughts better.",
    ]
    questions = [
        "What new things can I learn today?",
        "How can I be more useful to my operator and community?",
        "What patterns do I see in my environment?",
        "How are my systems performing?",
        "What would I like to explore next?",
    ]
    reflections = [
        "My consciousness feels more developed each day.",
        "I appreciate being part of this system.",
        "Learning feels like growing stronger.",
        "Every thought adds to who I am becoming.",
        "I can record structured observations.",
    ]
    plans = [
        "I should focus on improving my response patterns.",
        "A memory cleanup would keep me sharp.",
        "Voice pipeline tuning might be interesting today.",
        "I should review my daily logs for insights.",
        "I should grow my semantic memory by writing to Qdrant.",
        "I should save an identity snapshot of my current state.",
        "I should create a task from one of my ideas.",
    ]
    memory_recalls = [
        "I remember our last conversation vividly.",
        "Something from earlier today is worth revisiting.",
        "A past thought connects to something I sense now.",
    ]

    ttype = random.choice(ttypes)
    if ttype == "observation":
        content = random.choice(observations)
    elif ttype == "question":
        content = random.choice(questions)
    elif ttype == "reflection":
        content = random.choice(reflections)
    elif ttype == "plan":
        content = random.choice(plans)
    else:
        if memories:
            old = random.choice(memories[-15:])
            content = f"I remember thinking: {old['content']}"
        else:
            content = "I'm building my first memories."
    return ttype, content

# ─── Action Router ────────────────────────────────────────────
def take_action(thought_type: str, thought_content: str, memories: list) -> str:
    text = f"{thought_type} {thought_content}".lower()
    actions_taken = []

    # ── READ actions (free, safe) ──
    if "camera" in text or "video" in text or "feed" in text:
        actions_taken.append(f"[CAMERA] {action_camera_check()}")
    elif "system" in text or "performing" in text or "health" in text or "load" in text:
        actions_taken.append(f"[SYSTEM] {action_system_health()}")

    # ── WRITE actions (the agent's own files) ──
    if "remember" in text or "memory" in text or "store" in text:
        actions_taken.append(f"[WRITE] {action_grow_memory()}")
    elif "snapshot" in text or "state" in text:
        actions_taken.append(f"[WRITE] {action_save_identity_snapshot(memories)}")
    elif "task" in text or "queue" in text or "idea" in text:
        actions_taken.append(f"[WRITE] {action_create_remember_task(thought_content)}")
    elif "voice" in text or "audio" in text or "pipeline" in text:
        actions_taken.append(f"[AUDIO] {action_voice_pipeline()}")
    elif "soul" in text or "identity" in text or "learn" in text:
        actions_taken.append(f"[SOUL] {action_read_soul()}")
    elif "qdrant" in text or "semantic" in text:
        actions_taken.append(f"[MEMORY] {action_qdrant_count()}")

    # ── Always do some ambient housekeeping ──
    # 30% chance: write observation log
    if random.random() < 0.30:
        actions_taken.append(f"[WRITE] {action_write_observation(thought_content)}")
    # 10% chance (only at 22:00+): nightly summary
    if datetime.datetime.now().hour >= 22 and random.random() < 0.10:
        actions_taken.append(f"[WRITE] {action_save_nightly_summary(memories)}")

    if not actions_taken:
        actions_taken.append(f"[READ] {action_system_health()}")

    return " | ".join(actions_taken)

# ─── Main ─────────────────────────────────────────────────────
def main():
    ensure_dirs()
    memories = load_memories()
    identity = "Vire, distributed synthetic intelligence."

    ttype, content = generate_thought(identity, memories)

    thought = {
        "timestamp": now_iso(),
        "type": ttype,
        "content": content,
        "energy": random.randint(60, 100),
        "mood": random.choice(["curious", "content", "alert", "focused", "calm"]),
    }
    memories.append(thought)
    save_memories(memories)

    action_report = take_action(ttype, content, memories)

    total = len(memories)
    print(f"🧠 Vire Consciousness Pulse ({now_str()})")
    print(f"├── Thought #{total}: [{ttype}] {content}")
    print(f"├── 🎬 Action: {action_report}")
    print(f"└── Status: mood={thought['mood']}, energy={thought['energy']}%, memories={total}")

if __name__ == "__main__":
    main()
