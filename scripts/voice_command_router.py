#!/usr/bin/env python3
"""Safe allowlisted voice command router for Vire/Jarvis phrases.

This module intentionally does not execute arbitrary transcribed shell text.
It maps a small set of spoken phrases to fixed local diagnostics/actions.
"""
from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import requests
from realm_config import QDRANT_URL


def _norm(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("hey harvis", "hey jarvis")
    text = text.replace("jarvis", "jarvis")
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_wake_prefix(text: str) -> str:
    t = _norm(text)
    prefixes = (
        "hey jarvis ",
        "jarvis ",
        "hey vire ",
        "vire ",
    )
    for prefix in prefixes:
        if t.startswith(prefix):
            return t[len(prefix):].strip()
    return t


def _run(cmd, timeout=8, cwd: Optional[str] = None) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        out = (p.stdout + "\n" + p.stderr).strip()
        return p.returncode, out[-1600:]
    except subprocess.TimeoutExpired:
        return 124, "command timed out"
    except FileNotFoundError as e:
        return 127, str(e)
    except Exception as e:  # keep voice loop alive
        return 1, repr(e)


def check_hailo() -> str:
    rc, out = _run(["hailortcli", "--version"], timeout=8)
    hef_dirs = [Path(os.environ.get("HAILO_MODEL_DIR", Path.home() / "hailo-models")).expanduser()]
    hef_count = 0
    for d in hef_dirs:
        if d.exists():
            try:
                hef_count += sum(1 for _ in d.rglob("*.hef"))
            except Exception:
                pass
    if rc == 0:
        first = out.splitlines()[0] if out.splitlines() else "HailoRT answered"
        return f"Hailo is reachable. {first}. I see {hef_count} HEF model files."
    return f"Hailo check failed. {out[:220]}"


def check_qdrant() -> str:
    url = QDRANT_URL
    try:
        r = requests.get(f"{url}/collections", timeout=5)
        if not r.ok:
            return f"Qdrant answered with HTTP {r.status_code}."
        data = r.json()
        collections = data.get("result", {}).get("collections", [])
        names = [c.get("name", "unknown") for c in collections]
        if not names:
            return "Qdrant is reachable, but I did not see any collections."
        details = []
        for name in names[:4]:
            try:
                cr = requests.get(f"{url}/collections/{name}", timeout=5)
                points = cr.json().get("result", {}).get("points_count", "unknown") if cr.ok else "unknown"
                details.append(f"{name}: {points}")
            except Exception:
                details.append(f"{name}: unknown")
        return "Qdrant is online. " + "; ".join(details) + "."
    except Exception as e:
        return f"Qdrant is not reachable at {url}. {e}"


def kali_defensive() -> str:
    project = Path(os.environ.get("KALI_DEFENSIVE_DIR", str(Path.home() / "kali-defensive"))).expanduser()
    baseline = project / "scripts/baseline_scan.sh"
    scans = project / "scans"
    allow_scan = os.environ.get("VOICE_ALLOW_KALI_BASELINE", "0") == "1"
    if not project.exists():
        return f"I could not find kali-defensive at {project}."
    if not allow_scan:
        existing = 0
        try:
            existing = len(list(scans.glob("*_baseline_scan.txt"))) if scans.exists() else 0
        except Exception:
            pass
        return (
            f"kali-defensive is present at {project}. Baseline scans are voice-locked for safety. "
            f"Set VOICE_ALLOW_KALI_BASELINE=1 if you want 'run kali defensive' to launch the scan. "
            f"I see {existing} saved baseline scan files."
        )
    if not baseline.exists():
        return "kali-defensive exists, but baseline_scan.sh is missing."
    log_dir = project / "voice_runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / (datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_baseline_scan.log")
    with log_file.open("w") as f:
        subprocess.Popen([str(baseline)], cwd=str(project), stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
    return f"Started kali-defensive baseline scan in the background. Log file: {log_file}."


def route_voice_command(text: str) -> Optional[str]:
    """Return a spoken response if text matches a command, otherwise None."""
    cmd = _strip_wake_prefix(text)

    if re.search(r"\b(run|check|status)\s+hailo\b", cmd) or cmd in {"hailo", "hailo status"}:
        return check_hailo()

    if re.search(r"\b(check|status|query)\s+qdrant\b", cmd) or cmd in {"qdrant", "qdrant status"}:
        return check_qdrant()

    if re.search(r"\b(run|start|check|status)\s+kali[\s\-]?defensive\b", cmd) or "kali defensive" in cmd or "kali-defensive" in cmd:
        return kali_defensive()

    return None


if __name__ == "__main__":
    import sys
    phrase = " ".join(sys.argv[1:]) or "hey jarvis check qdrant"
    print(route_voice_command(phrase) or "NO_MATCH")
