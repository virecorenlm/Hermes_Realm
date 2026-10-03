#!/usr/bin/env python3
"""
auto_checkpoint.py — Background topic extractor + checkpoint daemon.

Runs every N minutes, detects topic shifts by comparing user message topics.
When a shift is found, extracts the completed topic block (from START to SHIFT-1),
summarizes, embeds to Qdrant, logs to daily file, and updates Redis state.

No user action required. Designed for cron every 15 minutes.

Redis state keys (in vire:auto_checkpoint:state):
  topic:        current topic name
  topic_start:  message id of first user msg in current topic
  topic_end:    message id of newest processed message

Usage:
    python3 auto_checkpoint.py --dry-run          # preview only
    python3 auto_checkpoint.py                      # normal mode
"""

import argparse
import sqlite3
import uuid
import datetime
import sys
import os
import re
import requests
import redis
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from realm_config import QDRANT_URL, OLLAMA_URL as BASE_OLLAMA_URL, REDIS_URL

# ── CONFIG ──────────────────────────────────────────────────────────
STATE_DB = os.path.expanduser("~/.hermes/state.db")
COLLECTION = "vire_memories"
OLLAMA_URL = BASE_OLLAMA_URL + "/api/embeddings"
MEMORY_DIR = os.path.expanduser("~/.openclaw/workspace/memory")
REDIS_PREFIX = "vire:auto_checkpoint"

MIN_MESSAGES = 3

# ── REDIS ────────────────────────────────────────────────────────────
def redis_conn():
    try:
        return redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    except Exception:
        return None


def get_redis_state(r) -> dict:
    defaults = {"topic": "", "topic_start": 0, "topic_end": 0}
    if not r:
        return defaults
    try:
        d = r.hgetall(f"{REDIS_PREFIX}:state") or {}
        return {
            "topic": d.get("topic", ""),
            "topic_start": int(d.get("topic_start", 0)),
            "topic_end": int(d.get("topic_end", 0)),
        }
    except Exception:
        return defaults


def save_redis_state(r, **kwargs):
    if not r:
        return
    try:
        r.hset(f"{REDIS_PREFIX}:state", mapping={k: str(v) for k, v in kwargs.items()})
    except Exception:
        pass


# ── EMBEDDING + QDRANT + LOG ────────────────────────────────────────
MAX_EMBED_LEN = 1500  # nomic-embed-text effective token window safety

def embed_text(text: str) -> list:
    clipped = text[:MAX_EMBED_LEN]
    resp = requests.post(OLLAMA_URL, json={"model": "nomic-embed-text:latest", "prompt": clipped}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    emb = data.get("embedding") or data.get("embeddings")
    if isinstance(emb, list) and len(emb) > 0:
        if isinstance(emb[0], list):
            return emb[0]
        return emb
    raise RuntimeError(f"Unexpected format: {data.keys()}")


def upsert_to_qdrant(point_id: str, vector: list, payload: dict):
    url = f"{QDRANT_URL}/collections/{COLLECTION}/points?wait=true"
    data = {"points": [{"id": point_id, "vector": vector, "payload": payload}]}
    resp = requests.put(url, json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def append_to_daily_log(entry: str) -> str:
    os.makedirs(MEMORY_DIR, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(MEMORY_DIR, f"{today}.md")
    with open(path, "a") as f:
        f.write(f"\n---\n## Auto-Checkpoint ({datetime.datetime.now().strftime('%H:%M')})\n\n{entry}\n")
    return path


# ── TOPIC EXTRACTION ──────────────────────────────────────────────────
def extract_topic_name(text: str) -> str:
    msg_lower = text.lower()
    # If message starts with continuation markers, treat as same topic
    continuation_markers = [
        r"^yeah", r"^ok[ay]?", r"^alright", r"^then", r"^also",
        r"^and", r"^so", r"^but", r"^i agree", r"^got it",
        r"^right", r"^sure", r"^cool", r"^nice",
    ]
    for marker in continuation_markers:
        if re.search(marker, msg_lower):
            return "SAME_TOPIC"

    # Look for keywords AFTER the first 30 chars (skip "Yeah, ok so...")
    search_text = text[30:].lower() if len(text) > 30 else text.lower()
    known = [
        ("hailo", r"hailo"),
        ("vision_pipeline", r"webcam|vision|camera|yolo|object detect"),
        ("voice_pipeline", r"voice|wake word|stt|tts|whisper|piper"),
        ("redis", r"\bredis\b"),
        ("dashboard", r"dashboard"),
        ("workforce", r"workforce|queen|agent|fleet"),
        ("email", r"\bemail|gmail|smtp|inbox"),
        ("shopify", r"shopify|store|bait.*tackle"),
        ("qdrant", r"qdrant|vector.*memory"),
        ("memory", r"\bmemory\b|forget|remember"),
        ("ollama", r"ollama|model.*pull|local.*llm"),
        ("security", r"secur|threat|defense|attack"),
        ("network", r"ssh|network|node.*down"),
        ("fishing", r"forecast|fishing.*report"),
        ("hardware", r"pi.*5|nvme|ram|cpu|gpu|hailo"),
        ("hermes", r"hermes|skill|config.*yaml"),
        ("topic_checkpoint", r"checkpoint|remember.*topic|save.*topic|auto.*checkpoint"),
        ("cron", r"cron.*job|auto.*extract"),
    ]
    for slug, pattern in known:
        if re.search(pattern, search_text):
            return slug
    # Fallback: first 3 significant words from search_text
    words = re.findall(r"[a-z]+", search_text)
    sig = [w for w in words if len(w) > 3 and w not in {
        "about", "could", "would", "should", "think", "something", "someone",
        "actually", "really", "though", "maybe", "probably", "definitely",
        "there", "their", "where", "which", "while",
    }]
    if sig:
        return "_".join(sig[:3])
    return "general"


def summarize_messages(messages: list) -> str:
    """Summary focused on topics, tasks, files, outcomes."""
    all_text = "\n".join(m.get("content", "") for m in messages if m.get("content"))
    lines = []

    tasks = re.findall(r"[-*] [\[\(]([ x>])[/\])] (.+)", all_text)
    if tasks:
        lines.append("Tasks:")
        for status, desc in tasks[:10]:
            marker = "✅" if status in {"x", "X", ">"} else "⏳"
            lines.append(f"  {marker} {desc.strip()}")

    paths = set(re.findall(r"[~]?/\S+\.\w+", all_text))
    if paths:
        lines.append("Files:")
        for p in sorted(paths)[:10]:
            lines.append(f"  {p}")

    outcomes = []
    for sentence in re.split(r"[.!?]\s+", all_text):
        if 10 < len(sentence) < 300:
            if re.search(r"\b(built|created|fixed|working|done|ready|saved|deployed)\b", sentence, re.I):
                outcomes.append(sentence.strip())
    if outcomes:
        lines.append("Outcomes:")
        for o in outcomes[:8]:
            lines.append(f"  {o}")

    if lines:
        return "Topic summary:\n" + "\n".join(lines)

    return "Conversation:\n" + "\n".join(
        f"[{m['role']}]: {m.get('content','')[:200]}" for m in messages[:8]
    )


# ── STATE.DB ──────────────────────────────────────────────────────────
def get_messages_between(start_id: int, end_id: int) -> list:
    """Get messages in range [start_id, end_id] inclusive, chronologically."""
    try:
        conn = sqlite3.connect(STATE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT session_id, role, content FROM messages "
            "WHERE id >= ? AND id <= ? ORDER BY id ASC",
            (start_id, end_id),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"DB error: {e}", file=sys.stderr)
        return []


def get_messages_after_id(after_id: int) -> list:
    """Get messages after after_id, newest first."""
    try:
        conn = sqlite3.connect(STATE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, session_id, role, content FROM messages WHERE id > ? ORDER BY id DESC",
            (after_id,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"DB error: {e}", file=sys.stderr)
        return []


# ── MAIN ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Auto-checkpoint conversation topics.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args()

    log = lambda msg: (not args.quiet) and print(msg)

    r = redis_conn()
    state = get_redis_state(r)
    current_topic = state.get("topic", "")
    topic_start_id = state.get("topic_start", 0)
    topic_end_id = state.get("topic_end", 0)

    # ── Get new messages ──
    new_messages = get_messages_after_id(topic_end_id)
    if not new_messages:
        log("No new messages.")
        return 0

    newest_message = max(m["id"] for m in new_messages)
    log(f"{len(new_messages)} new message(s). Range #{topic_end_id} → #{newest_message}")

    # ── Find FIRST user message in new batch (oldest first) ──
    first_user_in_batch = None
    for msg in reversed(new_messages):  # oldest to newest
        if msg.get("role") == "user":
            first_user_in_batch = msg
            break

    if not first_user_in_batch:
        # No user messages → just advance end marker and exit
        log("No user messages.")
        if not args.dry_run:
            save_redis_state(r, topic=current_topic, topic_start=topic_start_id, topic_end=newest_message)
        return 0

    user_topic = extract_topic_name(first_user_in_batch.get("content", ""))
    user_id = first_user_in_batch["id"]
    log(f"First user msg at #{user_id}: topic='{user_topic}'")

    if user_topic == "SAME_TOPIC" and current_topic:
        log(f"  → Continuation of '{current_topic}', advancing end to #{newest_message}")
        if not args.dry_run:
            save_redis_state(r, topic=current_topic, topic_start=topic_start_id, topic_end=newest_message)
        log("Done.")
        return 0

    log(f"Current topic: '{current_topic}' (start=#{topic_start_id}, end=#{topic_end_id})")

    if not current_topic:
        # First run or empty topic — initialize from this user message
        log(f"First run: setting topic to '{user_topic}'")
        if not args.dry_run:
            save_redis_state(r, topic=user_topic, topic_start=user_id, topic_end=newest_message)
        log(f"State initialized: topic='{user_topic}', start={user_id}, end={newest_message}")
        return 0

    if user_topic != current_topic:
        # ── TOPIC SHIFT → checkpoint previous topic ──
        log(f"  → Shift: '{current_topic}' → '{user_topic}'")
        block = get_messages_between(topic_start_id, user_id - 1)

        if block and "user" in {m["role"] for m in block} and len(block) >= MIN_MESSAGES:
            summary = summarize_messages(block)
            payload = {
                "text": summary,
                "topic": current_topic,
                "source": "auto_checkpoint",
                "date": datetime.datetime.now().isoformat(),
                "session_id": block[0].get("session_id", ""),
                "node": "pi5",
                "tags": ["auto", "checkpoint", current_topic],
            }

            if args.dry_run:
                log(f"  [DRY RUN] Would checkpoint '{current_topic}' ({len(block)} msgs):")
                log(f"  {summary[:400]}...")
            else:
                try:
                    vector = embed_text(summary)
                    point_id = str(uuid.uuid4())
                    upsert_to_qdrant(point_id, vector, payload)
                    log_path = append_to_daily_log(f"**Auto Checkpoint: {current_topic}**\n\n{summary}")
                    log(f"  ✅ '{current_topic}' → Qdrant + {log_path}")
                except Exception as e:
                    log(f"  ⚠️ Failed: {e}")
                    return 1
        else:
            log(f"  Skipped: {len(block)} msgs, roles={[m['role'] for m in block]}")

        # ── New topic state ──
        if not args.dry_run:
            save_redis_state(r, topic=user_topic, topic_start=user_id, topic_end=newest_message)
    else:
        # ── Same topic → just advance end marker ──
        log(f"  → Same topic '{current_topic}', advancing end to #{newest_message}")
        if not args.dry_run:
            save_redis_state(r, topic=current_topic, topic_start=topic_start_id, topic_end=newest_message)

    log("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
