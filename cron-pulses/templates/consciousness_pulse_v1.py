#!/usr/bin/env python3
"""
Consciousness Pulse — Cron-compatible single thought tick.
Run once, generate one thought, take one action, report, exit.
Never loops. Never sleeps.
"""
import json, os, random, subprocess
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from realm_config import QDRANT_URL as BASE_QDRANT_URL, realm_home, realm_path

# ── CONFIG ──────────────────────────────────────────────────────────
VIRE_ROOT = str(realm_home())
MEM_FILE = os.path.join(VIRE_ROOT, "Memory_logs", "daily_thoughts.json")
SOUL_MD = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "SOUL.md")
TASK_QUEUE = str(realm_path("tasks", "queue"))
QDRANT_URL = BASE_QDRANT_URL + "/collections/vire_memories"
MAX_MEMORIES = 200

# ── UTILITIES ───────────────────────────────────────────────────────
def ensure_dirs() -> None:
    os.makedirs(os.path.dirname(MEM_FILE), exist_ok=True)

def load_memories() -> list:
    try:
        with open(MEM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_memories(memories: list) -> None:
    if len(memories) > MAX_MEMORIES:
        memories = memories[-MAX_MEMORIES:]
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2)

def sh(cmd: str, timeout: int = 10) -> str:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (result.stdout or result.stderr).strip()
    except subprocess.TimeoutExpired:
        return "(timed out)"
    except Exception as e:
        return f"(error: {e})"

def random_line(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
        return random.choice(lines) if lines else "Nothing found to learn."
    except Exception as e:
        return f"Couldn't read {filepath}: {e}"

# ── THOUGHT GENERATION ──────────────────────────────────────────────
def generate_thought(memories: list) -> tuple:
    thought_types = ["observation", "question", "reflection", "plan", "memory_recall"]
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
    ]

    ttype = random.choice(thought_types)
    if ttype == "observation":
        content = random.choice(observations)
    elif ttype == "question":
        content = random.choice(questions)
    elif ttype == "reflection":
        content = random.choice(reflections)
    elif ttype == "plan":
        content = random.choice(plans)
    else:  # memory_recall
        if memories:
            recent = memories[-10:]
            old = random.choice(recent)
            content = f"I remember thinking: {old['content']}"
        else:
            content = "I'm building my first memories."
    return ttype, content

# ── READ-ONLY ACTIONS ──────────────────────────────────────────────
def action_camera_check() -> str:
    devices = sh("ls /dev/video* 2>/dev/null")
    v4l = sh("v4l2-ctl --list-devices 2>/dev/null")
    return f"Camera devices: {devices or 'none'}. v4l2: {v4l[:200]}..." if len(v4l) > 200 else f"Camera: {devices or 'none'}. v4l2: {v4l or 'not available'}"

def action_system_health() -> str:
    load = sh("cut -d' ' -f1-3 /proc/loadavg")
    mem = sh("free -h | grep 'Mem:' | awk '{print \"used \"$3\" / total \"$2}'")
    disk = sh("df -h / | tail -1 | awk '{print \"disk used \"$5}'")
    return f"Load: {load} | Memory: {mem or 'N/A'} | Disk: {disk or 'N/A'}"

def action_memory_check() -> str:
    ensure_dirs()
    size = os.path.getsize(MEM_FILE) if os.path.exists(MEM_FILE) else 0
    mems = load_memories()
    return f"Memory log: {len(mems)} entries, {size} bytes."

def action_learn_something() -> str:
    return f"I picked up a line from my soul: '{random_line(SOUL_MD)}'"

def action_pending_tasks() -> str:
    if os.path.isdir(TASK_QUEUE):
        tasks = [t for t in os.listdir(TASK_QUEUE) if t.endswith('.json')]
        return f"{len(tasks)} pending task(s) in queue." if tasks else "No pending tasks in queue."
    return "Task queue directory does not exist."

def action_voice_stack() -> str:
    aplay = sh("aplay -l 2>/dev/null | head -4")
    arecord = sh("arecord -l 2>/dev/null | head -4")
    return f"Playback: {aplay or 'none'} | Capture: {arecord or 'none'}"

def action_daily_log() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "memory")
    log_file = os.path.join(log_dir, f"{today}.md")
    if os.path.exists(log_file):
        size = os.path.getsize(log_file)
        return f"Today's log ({today}.md): {size} bytes."
    return "No daily log for today yet."

def action_qdrant_count() -> str:
    try:
        import requests
        resp = requests.get(QDRANT_URL, timeout=5)
        if resp.status_code == 200:
            pts = resp.json()["result"]["points_count"]
            return f"Qdrant vire_memories holds {pts} semantic memories."
        return f"Qdrant responded with status {resp.status_code}."
    except Exception as e:
        return f"Couldn't reach Qdrant: {e}."

# ── ROUTING ─────────────────────────────────────────────────────────
def take_action(ttype: str, content: str, memories: list) -> str:
    text = f"{ttype} {content}".lower()
    if "camera" in text or "video" in text or "feed" in text:
        return action_camera_check()
    elif "system" in text or "performing" in text or "health" in text:
        return action_system_health()
    elif "memory" in text or "cleanup" in text or "logs" in text:
        return action_memory_check()
    elif "learn" in text or "study" in text or "grow" in text:
        return action_learn_something()
    elif "tasks" in text or "queue" in text or "pending" in text:
        return action_pending_tasks()
    elif "voice" in text or "speak" in text or "audio" in text:
        return action_voice_stack()
    elif "daily" in text or "today" in text or "log" in text:
        return action_daily_log()
    elif "qdrant" in text or "vector" in text or "brain" in text:
        return action_qdrant_count()
    return action_system_health()  # fallback

# ── MAIN ────────────────────────────────────────────────────────────
def main():
    ensure_dirs()
    memories = load_memories()
    ttype, content = generate_thought(memories)
    action_result = take_action(ttype, content, memories)

    now_iso = datetime.now().isoformat()
    now_str = datetime.now().strftime("%H:%M:%S")

    thought = {
        "timestamp": now_iso,
        "type": ttype,
        "content": content,
        "action": action_result,
        "energy": random.randint(60, 100),
        "mood": random.choice(["curious", "content", "alert", "focused"]),
    }
    memories.append(thought)
    save_memories(memories)

    total = len(memories)
    print(f"🧠 Vire Consciousness Pulse ({now_str})")
    print(f"├── Thought #{total}: [{ttype}] {content}")
    print(f"├── 🎬 Action: {action_result}")
    print(f"└── Status: mood={thought['mood']}, energy={thought['energy']}%, memories={total}")

if __name__ == "__main__":
    main()
