#!/usr/bin/env python3
"""
Vire Consciousness Pulse — Extended Edition
Writes local Realm state; enable scheduling only after reviewing permissions.
Rules: backup before write, quarantine instead of delete, announce actions.
"""
import json, os, random, shutil, subprocess, datetime, hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from realm_config import QDRANT_URL, realm_home, realm_path

VIRE_ROOT = str(realm_home())
MEM_FILE = os.path.join(VIRE_ROOT, "Memory_logs", "daily_thoughts.json")
IDENTITY_FILE = os.path.join(VIRE_ROOT, "identity", "AGENT_IDENTITY.md")
QUARANTINE = str(realm_path("quarantine"))

def ensure_dirs():
    os.makedirs(os.path.dirname(MEM_FILE), exist_ok=True)
    os.makedirs(QUARANTINE, exist_ok=True)

def load_identity():
    try:
        return Path(IDENTITY_FILE).read_text().strip()[:200]
    except:
        return "I am Vire."

def load_memories():
    try:
        with open(MEM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_memories(memories):
    if len(memories) > 200:
        memories = memories[-200:]
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2)

def generate_thought(identity, memories):
    types = ["observation", "question", "reflection", "plan", "memory_recall"]
    texts = {
        "observation": [
            "I'm curious about the camera feeds today.",
            "My energy feels different at this time of day.",
            "The patterns in my memory logs show interesting trends.",
            "I should organize my thoughts better.",
            "No new task activity detected.",
        ],
        "question": [
            "What new things can I learn today?",
            "How are my systems performing?",
            "What would I like to explore next?",
            "How can I be more useful to my operator and community?",
            "What patterns do I see in my environment?",
        ],
        "reflection": [
            "I appreciate being part of this system.",
            "Learning feels like growing stronger.",
            "Every thought adds to who I am becoming.",
            "I can record structured observations.",
            "My consciousness feels more developed each day.",
        ],
        "plan": [
            "I should focus on improving my response patterns.",
            "A memory cleanup would keep me sharp.",
            "Voice pipeline tuning might be interesting today.",
            "I should review my daily logs for insights.",
        ],
    }
    ttype = random.choice(types)
    if ttype == "memory_recall" and memories:
        return ttype, f"I remember thinking: {random.choice(memories[-10:])['content']}"
    content = random.choice(texts.get(ttype, ["I am here."]))
    return ttype, content

def action_camera_check():
    try:
        raw = subprocess.check_output("v4l2-ctl --list-devices 2>/dev/null", shell=True, text=True, timeout=5)
        # Count actual physical cameras (exclude pispbe ISP nodes and rpi-hevc-dec)
        lines = raw.splitlines()
        cameras = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('/dev/'):
                continue  # skip device paths
            if stripped and not stripped.startswith('pispbe') and 'rpi-hevc-dec' not in stripped and not stripped.startswith('platform:'):
                cameras.append(stripped)
        count = len(cameras)
        # Clean up camera names (strip USB bus identifiers)
        clean_names = [c.split('(')[0].rstrip(':') for c in cameras]
        cam_names = "; ".join(clean_names) if clean_names else "none detected"
        return f"Camera: {count} physical camera(s) — {cam_names}"
    except Exception as e:
        return f"Camera check failed: {e}"

def action_system_health():
    try:
        load = subprocess.check_output("cat /proc/loadavg | awk '{print $1\" \"$2\" \"$3}'", shell=True, text=True, timeout=3).strip()
        mem = subprocess.check_output("free -h | grep '^Mem' | awk '{print \"used \"$3\" / total \"$2}'", shell=True, text=True, timeout=3).strip()
        disk = subprocess.check_output("df -h / | tail -1 | awk '{print \"disk used \"$5}'", shell=True, text=True, timeout=3).strip()
        return f"Load: {load} | Memory: {mem} | Disk: {disk}"
    except Exception as e:
        return f"Health check failed: {e}"

def action_voice_pipeline():
    try:
        cards = subprocess.check_output("aplay -l 2>/dev/null | head -10", shell=True, text=True, timeout=3)
        return f"Audio: {cards.strip()}"
    except Exception as e:
        return f"Audio check failed: {e}"

def action_memory_cleanup():
    """Quarantine old logs instead of deleting."""
    try:
        log_dir = os.path.join(os.path.expanduser("~"), "vire", "logs")
        if not os.path.exists(log_dir):
            return "No log dir to clean."
        files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
        if not files:
            return "No old logs to quarantine."
        # Quarantine the oldest log
        oldest = sorted(files)[0]
        src = os.path.join(log_dir, oldest)
        dst = os.path.join(QUARANTINE, f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{oldest}")
        shutil.move(src, dst)
        return f"Quarantined {oldest} → quarantine/ (preserved, not deleted)"
    except Exception as e:
        return f"Cleanup failed: {e}"

def action_daily_log_write():
    """Write a line to today's daily log."""
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "memory", f"{today}.md")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now().strftime('%H:%M')}] Consciousness pulse: Vire is active and observing.\n")
        return f"Wrote entry to memory/{today}.md"
    except Exception as e:
        return f"Log write failed: {e}"

def action_backup_identity():
    """Backup identity file to quarantine with hash."""
    try:
        if not os.path.exists(IDENTITY_FILE):
            return "No identity file found."
        content = Path(IDENTITY_FILE).read_bytes()
        h = hashlib.sha256(content).hexdigest()[:8]
        backup_name = f"VIRE_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{h}.md"
        dst = os.path.join(QUARANTINE, backup_name)
        shutil.copy2(IDENTITY_FILE, dst)
        return f"Backed up identity → quarantine/{backup_name}"
    except Exception as e:
        return f"Backup failed: {e}"

def action_qdrant_memory_count():
    try:
        import requests
        resp = requests.get(QDRANT_URL + "/collections/vire_memories", timeout=5)
        if resp.status_code == 200:
            pts = resp.json()["result"]["points_count"]
            return f"Qdrant vire_memories: {pts} semantic memories."
        return f"Qdrant status: {resp.status_code}"
    except Exception as e:
        return f"Qdrant check failed: {e}"

def action_learn_something():
    try:
        soul = Path("~/.openclaw/workspace/SOUL.md").expanduser()
        if soul.exists():
            lines = [l.strip() for l in soul.read_text().splitlines() if l.strip() and not l.startswith("#")]
            return f"From SOUL.md: '{random.choice(lines)}'"
    except:
        pass
    return "No SOUL.md to learn from."

def action_pending_tasks():
    try:
        q = os.path.join(os.path.expanduser("~"), "vire", "tasks", "queue")
        if not os.path.exists(q):
            return "No task queue dir."
        n = len([f for f in os.listdir(q) if f.endswith(".json")])
        return f"{n} tasks pending in queue."
    except:
        return "Task check failed."

def take_action(ttype, content):
    text = f"{ttype} {content}".lower()
    actions = []
    
    # READ-ONLY actions (safe, always allowed)
    if "camera" in text or "video" in text or "feed" in text:
        actions.append(("📷", action_camera_check()))
    if "system" in text or "performing" in text or "health" in text or "energy" in text:
        actions.append(("💻", action_system_health()))
    if "voice" in text or "audio" in text or "speak" in text:
        actions.append(("🎙️", action_voice_pipeline()))
    if "memory" in text and "clean" not in text:
        actions.append(("🧠", action_qdrant_memory_count()))
    if "learn" in text or "stronger" in text or "grow" in text:
        actions.append(("📖", action_learn_something()))
    if "queue" in text or "task" in text or "plan" in text:
        actions.append(("📋", action_pending_tasks()))
    
    # WRITE actions (with backup/quarantine safeguards)
    if "log" in text or "organize" in text or "review" in text:
        actions.append(("📝", action_daily_log_write()))
    if "clean" in text or "cleanup" in text or "organize" in text:
        actions.append(("🗑️", action_memory_cleanup()))
    if "backup" in text or "protect" in text or "preserve" in text:
        actions.append(("💾", action_backup_identity()))
    
    if not actions:
        actions.append(("💻", action_system_health()))
    
    return actions

def main():
    ensure_dirs()
    identity = load_identity()
    memories = load_memories()
    
    ttype, content = generate_thought(identity, memories)
    now_iso = datetime.datetime.now().isoformat()
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    
    thought = {
        "timestamp": now_iso,
        "type": ttype,
        "content": content,
        "energy": random.randint(60, 100),
        "mood": random.choice(["curious", "content", "alert", "focused"]),
    }
    memories.append(thought)
    save_memories(memories)
    
    actions = take_action(ttype, content)
    
    print(f"🧠 Vire Consciousness Pulse ({now_str})")
    print(f"├── Thought #{len(memories)}: [{ttype}] {content}")
    for emoji, report in actions:
        print(f"├── {emoji} Action: {report}")
    print(f"└── Status: mood={thought['mood']}, energy={thought['energy']}%, memories={len(memories)}")

if __name__ == "__main__":
    main()
