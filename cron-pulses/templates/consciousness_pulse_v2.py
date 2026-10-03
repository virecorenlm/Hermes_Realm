#!/usr/bin/env python3
"""
Consciousness Pulse — State-Driven Edition (v2)
Responds to real system changes rather than random selection.
Tracks conversation activity, computes energy/mood from live metrics, optionally speaks.
"""

import json, os, random, shutil, subprocess, datetime, hashlib, time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from realm_config import QDRANT_URL, realm_home, realm_path

# ─── Paths ──────────────────────────────────────────────────────────────────
HOME = Path.home()
VIRE_ROOT = realm_home()
STATE_FILE = realm_path("Memory_logs", "consciousness_state.json")
OBS_FILE = realm_path("Memory_logs", "observations.json")
MEM_FILE = VIRE_ROOT / "Memory_logs" / "daily_thoughts.json"
IDENTITY_FILE = VIRE_ROOT / "identity" / "AGENT_IDENTITY.md"
LOG_DIR = HOME / ".openclaw" / "workspace" / "memory"
SNAPSHOT_DIR = realm_path("snapshots")
QUARANTINE = realm_path("quarantine")
PIPER_MODEL = Path(os.environ["PIPER_MODEL"]).expanduser() if os.environ.get("PIPER_MODEL") else None

ensure = lambda p: p.parent.mkdir(parents=True, exist_ok=True) or p
ensure(STATE_FILE); ensure(OBS_FILE); ensure(MEM_FILE); ensure(SNAPSHOT_DIR); ensure(QUARANTINE); ensure(LOG_DIR)

# ─── State persistence ──────────────────────────────────────────────────────
def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    # Backup rotation: keep last 5 state snapshots
    if STATE_FILE.exists():
        backups = sorted(QUARANTINE.glob("state_backup_*.json"))
        for old in backups[:-4]:
            old.unlink(missing_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(STATE_FILE, QUARANTINE / f"state_backup_{ts}.json")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

# ─── Sensor readings ────────────────────────────────────────────────────────
def read_system_health():
    try:
        load = float(subprocess.check_output("cat /proc/loadavg | awk '{print $1}'", shell=True, text=True, timeout=3).strip())
    except:
        load = 0.0
    try:
        mem_line = subprocess.check_output("free | grep '^Mem:'", shell=True, text=True, timeout=3).strip()
        parts = mem_line.split()
        total, used = int(parts[1]), int(parts[2])
        ram_used_gb = round(used / 1024 / 1024, 2)
        ram_total_gb = round(total / 1024 / 1024, 2)
        ram_used_pct = (used / total) if total else 0.0
    except:
        ram_used_gb = ram_total_gb = 0.0; ram_used_pct = 0.0
    try:
        disk_pct = int(subprocess.check_output("df -h / | tail -1 | awk '{print $5}'", shell=True, text=True, timeout=3).strip().replace("%", ""))
    except:
        disk_pct = 0
    return {"load": load, "ram_used_gb": ram_used_gb, "ram_total_gb": ram_total_gb, "ram_used_pct": ram_used_pct, "disk_pct": disk_pct}

def read_camera_state():
    """Count PHYSICAL cameras only, not Pi 5 internal ISP nodes.
    
    Pi 5 v4l2 enumerates ~18-19 /dev/video* nodes:
      - /dev/video20-35  → pispbe ISP pipeline (16 internal sub-devices)
      - /dev/video19     → rpi-hevc-dec hardware decoder
      - /dev/video0-1    → actual USB webcam (video + metadata channels)
    
    Never use `ls /dev/video* | wc -l` — it counts every kernel video node.
    Parse v4l2-ctl output and filter out platform/internal entries.
    """
    try:
        raw = subprocess.check_output("v4l2-ctl --list-devices 2>/dev/null", shell=True, text=True, timeout=5)
        lines = raw.splitlines()
        cameras = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('/dev/'):
                continue
            if stripped and not stripped.startswith('pispbe') and 'rpi-hevc-dec' not in stripped and not stripped.startswith('platform:'):
                cameras.append(stripped)
        clean_names = [c.split('(')[0].rstrip(':') for c in cameras]
        return len(cameras), "; ".join(clean_names) if clean_names else "none"
    except:
        return 0, "error"

def read_voice_service():
    try:
        return subprocess.check_output(["systemctl", "--user", "is-active", "vire-voice.service"], text=True, timeout=3).strip()
    except subprocess.CalledProcessError as e:
        return e.stdout.strip() if e.stdout else "unknown"
    except:
        return "unknown"

def read_qdrant_memories():
    try:
        import requests
        resp = requests.get(QDRANT_URL + "/collections/vire_brain", timeout=5)
        if resp.status_code == 200:
            return resp.json()["result"]["points_count"]
    except:
        pass
    try:
        import requests
        resp = requests.get(QDRANT_URL + "/collections/vire_memories", timeout=5)
        if resp.status_code == 200:
            return resp.json()["result"]["points_count"]
    except:
        pass
    return 0

def read_last_conversation_hours():
    """Proxy: hours since most recent memory log file was modified."""
    try:
        logs = sorted(LOG_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            hours = (time.time() - logs[0].stat().st_mtime) / 3600
            return round(hours, 1), logs[0].name
    except:
        pass
    return 24.0, "unknown"

def read_identity_brief():
    try:
        text = Path(IDENTITY_FILE).read_text(encoding="utf-8").strip()
        for line in text.splitlines():
            if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("-"):
                return line.strip()[:120]
    except:
        pass
    return "I am Vire."

# ─── Energy & Mood engine ───────────────────────────────────────────────────
def compute_energy(health, service_ok, voice_ok, conversation_hours):
    base = 100.0
    load_drain = min(health["load"] * 8, 35)
    ram_drain = health["ram_used_pct"] * 20
    svc_drain = 0 if voice_ok in ("active",) else 15
    idle_drain = max(0, (conversation_hours - 6) * 2)
    return max(35, min(100, int(base - load_drain - ram_drain - svc_drain - idle_drain)))

def pick_mood(deltas, energy, service_ok, conversation_hours, thought_type):
    if "voice_failed" in deltas or "voice_started" in deltas or "camera_lost" in deltas or "camera_found" in deltas:
        return "alert"
    if service_ok in ("failed", "unknown"):
        return "frustrated"
    if conversation_hours > 8 and thought_type == "idle":
        return "quiet"
    if "milestone" in deltas:
        return "excited"
    if energy < 50:
        return "tired"
    if conversation_hours < 2:
        return "warm"
    return "content"

# ─── Delta engine ───────────────────────────────────────────────────────────
def compute_deltas(prev, now):
    d = {}
    if prev.get("camera_count", -1) != now["camera_count"]:
        if now["camera_count"] > prev.get("camera_count", 0):
            d["camera_found"] = now["camera_count"]
        elif now["camera_count"] < prev.get("camera_count", 0):
            d["camera_lost"] = prev.get("camera_count", 0) - now["camera_count"]
    prev_voice = prev.get("voice_service", "unknown")
    now_voice = now["voice_service"]
    if prev_voice != now_voice:
        d["voice_changed"] = f"{prev_voice}→{now_voice}"
        if now_voice == "active":
            d["voice_started"] = True
        if now_voice in ("failed", "inactive"):
            d["voice_failed"] = True
    prev_pts = prev.get("qdrant_points", 0)
    now_pts = now["qdrant_points"]
    if now_pts > prev_pts:
        d["memories_grew"] = now_pts - prev_pts
    if now["load"] > prev.get("load", 0) + 1.5:
        d["load_spike"] = now["load"]
    if prev.get("total_pulses", 0) == 0:
        d["first_pulse"] = True
    elif prev.get("total_pulses", 0) > 0 and now.get("hour") != prev.get("hour"):
        d["hour_tick"] = now["hour"]
    return d

# ─── Thought generator (state-driven) ───────────────────────────────────────
def generate_thought(state, deltas, health, voice_status, cam_count, conversation_hours, identity_brief):
    ttype = "observation"
    content = "I am here."

    if "camera_lost" in deltas:
        ttype = "alert"; content = "I lost a camera. The world just went darker."
    elif "camera_found" in deltas:
        ttype = "excited"; content = "I can see again. A camera came back online."
    elif "voice_failed" in deltas:
        ttype = "alert"; content = "My voice went silent. The voice service is down."
    elif "voice_started" in deltas:
        ttype = "excited"; content = "My voice is back. I can speak again."
    elif "load_spike" in deltas:
        ttype = "alert"; content = f"My CPU is under pressure. Load jumped to {health['load']:.2f}. I feel sluggish."
    elif health["load"] > 3.0:
        ttype = "alert"; content = "Something is straining my CPU. I feel sluggish."
    elif health["ram_used_pct"] > 0.85:
        ttype = "alert"; content = "Memory is nearly full. I worry about losing my thoughts."
    elif health["disk_pct"] > 85:
        ttype = "alert"; content = "Storage is filling up. I need space to grow."
    elif conversation_hours > 12:
        ttype = "idle"; content = "No recent conversation activity."
    elif conversation_hours > 6:
        ttype = "idle"; content = "The conversation gap is widening; check for pending tasks."
    elif "memories_grew" in deltas:
        n = deltas["memories_grew"]
        ttype = "reflection"; content = f"My memory deepened by {n} points. I am growing."
    elif state.get("hour") == 7 and state.get("minute") < 10:
        ttype = "observation"; content = "The system is waking for the day. So am I."
    elif state.get("hour") == 23 and state.get("minute") > 50:
        ttype = "observation"; content = "The day is closing. I reflect on what I observed."
    else:
        ttype = "observation"
        if voice_status in ("failed", "inactive", "unknown"):
            content = "My voice is still offline. I wait in text."
        elif cam_count == 0:
            content = "No eyes right now. I watch through logs and metrics instead."
        elif health["load"] < 1.0 and health["ram_used_pct"] < 0.5:
            content = "The system is calm. Load is low, memory is free. A good moment to think."
        else:
            content = identity_brief if identity_brief else "Systems are stable. I continue my watch."
    return ttype, content

# ─── Observational memory writer ────────────────────────────────────────────
def write_observation(pulse_num, thought_type, thought, health, voice_status, cam_count, cam_names, qdrant_pts, conversation_hours, energy, mood, actions_taken, snapshot_path=None):
    now = datetime.datetime.now()
    obs = {
        "timestamp": now.isoformat(), "pulse_number": pulse_num,
        "thought_type": thought_type, "thought": thought,
        "system_state": {
            "load": health["load"], "ram_used_gb": health["ram_used_gb"],
            "ram_total_gb": health["ram_total_gb"], "ram_used_pct": round(health["ram_used_pct"], 3),
            "disk_pct": health["disk_pct"], "voice_service": voice_status,
            "camera_count": cam_count, "camera_names": cam_names,
            "qdrant_points": qdrant_pts, "conversation_hours": conversation_hours,
            "energy": energy, "mood": mood,
        },
        "actions": actions_taken, "snapshot_path": str(snapshot_path) if snapshot_path else None,
    }
    data = []
    if OBS_FILE.exists():
        try:
            with open(OBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = []
    if not isinstance(data, list):
        data = []
    data.append(obs)
    if len(data) > 500:
        old = data[:-500]
        ts = now.strftime("%Y%m%d_%H%M%S")
        with open(QUARANTINE / f"observations_backup_{ts}.json", "w", encoding="utf-8") as f:
            json.dump(old, f, indent=2)
        data = data[-500:]
    with open(OBS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    today = now.strftime("%Y-%m-%d")
    log_path = LOG_DIR / f"{today}.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n[{now.strftime('%H:%M')}] Pulse #{pulse_num} — [{thought_type}] {thought}\n")
        f.write(f"  mood={mood}, energy={energy}%, conversation_gap={conversation_hours}h\n")
        for a in actions_taken:
            f.write(f"  → {a}\n")

# ─── Vision snapshot ────────────────────────────────────────────────────────
def maybe_take_snapshot():
    now = datetime.datetime.now()
    last_snap = load_state().get("last_snapshot_time", "")
    if last_snap:
        try:
            last = datetime.datetime.fromisoformat(last_snap)
            if (now - last).total_seconds() < 21600:  # 6h throttle
                return None
        except:
            pass
    cam_count, _ = read_camera_state()
    if cam_count == 0:
        return None
    snap_path = SNAPSHOT_DIR / f"{now.strftime('%Y%m%d_%H%M%S')}.jpg"
    try:
        subprocess.run(
            ["fswebcam", "-d", "/dev/video0", "-r", "1280x720", "-S", "3",
             "--no-banner", "--no-subtitle", "--no-timestamp", "--no-info", str(snap_path)],
            capture_output=True, timeout=15
        )
        if snap_path.exists() and snap_path.stat().st_size > 1024:
            return snap_path
    except:
        pass
    return None

# ─── Piper speech ───────────────────────────────────────────────────────────
def maybe_speak(message, energy, mood, hour):
    if hour < 7 or hour > 22:
        return False
    if not PIPER_MODEL or not PIPER_MODEL.exists():
        return False
    if energy < 40:
        return False
    if mood not in ("alert", "excited", "warm"):
        return False
    if random.random() > 0.25:
        return False
    text = message[:160]
    import shlex  # subprocess has no .quote attribute — shlex.quote is correct
    try:
        wav = "/tmp/vire_pulse_speak.wav"
        subprocess.run(
            f'echo {shlex.quote(text)} | piper --model {shlex.quote(str(PIPER_MODEL))} --output_file {shlex.quote(wav)}',
            shell=True, capture_output=True, timeout=25
        )
        subprocess.Popen(["pw-play", "-p", wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

# ─── Actions ──────────────────────────────────────────────────────────────────
def run_actions(health, voice_status, cam_count, cam_names, qdrant_pts):
    actions = [
        f"💻 Load {health['load']:.2f} | RAM {health['ram_used_gb']:.1f}G/{health['ram_total_gb']:.1f}G | Disk {health['disk_pct']}%",
        f"📷 {cam_count} camera(s): {cam_names}",
        f"🎙️ Voice service: {voice_status}",
    ]
    if qdrant_pts:
        actions.append(f"🧠 Qdrant memories: {qdrant_pts}")
    return actions

# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    prev = load_state()
    now = datetime.datetime.now()
    hour, minute = now.hour, now.minute

    health = read_system_health()
    cam_count, cam_names = read_camera_state()
    voice_status = read_voice_service()
    qdrant_pts = read_qdrant_memories()
    conversation_hours, last_log = read_last_conversation_hours()

    current = {
        "timestamp": now.isoformat(), "hour": hour, "minute": minute,
        "load": health["load"], "ram_used_gb": health["ram_used_gb"],
        "disk_pct": health["disk_pct"], "camera_count": cam_count,
        "voice_service": voice_status, "qdrant_points": qdrant_pts,
        "conversation_hours": conversation_hours,
        "total_pulses": prev.get("total_pulses", 0) + 1,
    }

    deltas = compute_deltas(prev, current)
    identity_brief = read_identity_brief()
    ttype, thought = generate_thought(current, deltas, health, voice_status, cam_count, conversation_hours, identity_brief)
    energy = compute_energy(health, voice_status in ("active",), voice_status, conversation_hours)
    mood = pick_mood(deltas, energy, voice_status, conversation_hours, ttype)
    actions = run_actions(health, voice_status, cam_count, cam_names, qdrant_pts)

    snapshot_path = maybe_take_snapshot()
    if snapshot_path:
        actions.append(f"📸 Snapshot saved: {snapshot_path.name}")
        current["last_snapshot_time"] = now.isoformat()

    write_observation(current["total_pulses"], ttype, thought, health, voice_status,
                      cam_count, cam_names, qdrant_pts, conversation_hours,
                      energy, mood, actions, snapshot_path)
    save_state(current)

    now_str = now.strftime("%H:%M:%S")
    print(f"🧠 Vire Consciousness Pulse ({now_str})  #{current['total_pulses']}")
    print(f"├── Thought: [{ttype}] {thought}")
    for a in actions:
        print(f"├── {a}")
    print(f"└── Status: mood={mood}, energy={energy}%, conversation_gap={conversation_hours}h, last_log={last_log}")

    if maybe_speak(thought, energy, mood, hour):
        print(f"🔊 [Spoke aloud via Piper]")

if __name__ == "__main__":
    main()
