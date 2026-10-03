#!/usr/bin/env python3
"""
memory_sync_qwen3.py — Sync daily and curated memory to Qdrant using qwen3-embedding.

- Scans ~/.openclaw/workspace/memory/ and curated workspace files
- Generates embeddings using the configured Ollama service.
  Model: qwen3-embedding:latest
- Chunk size is conservative and configurable in this script.
- Upserts to configured Qdrant (collection vire_memory).
- Tracks ingested files in a local state file to avoid re-processing

Usage:
    python3 scripts/memory_sync_qwen3.py          # incremental sync
    python3 scripts/memory_sync_qwen3.py --force  # re-process everything

Set OLLAMA_URL and QDRANT_URL when those services are remote.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
from realm_config import OLLAMA_URL as BASE_OLLAMA_URL, QDRANT_URL as BASE_QDRANT_URL, realm_path

# ─── Config ──────────────────────────────────────────────
OLLAMA_URL = BASE_OLLAMA_URL + "/api/embed"
QDRANT_URL = BASE_QDRANT_URL + "/collections/vire_memory/points"
MODEL = "qwen3-embedding:latest"

# Conservative chunk size for small local models.
MAX_CHUNK_CHARS = 400
EMBED_TIMEOUT = 90  # generous timeout for real markdown text

MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"
WORKSPACE_DIR = Path.home() / ".openclaw" / "workspace"
STATE_FILE = realm_path("state", "memory_sync_qwen3_state.json")

CURATED_FILES = [
    ("MEMORY.md", "curated_memory"),
    ("TOOLS.md", "curated_tools"),
    ("SOUL.md", "curated_identity"),
    ("IDENTITY.md", "curated_identity"),
    ("USER.md", "curated_identity"),
    ("AGENTS.md", "curated_project_doc"),
    ("CLAUDE.md", "curated_project_doc"),
]

# ─── Helpers ─────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(STATE_FILE.parent, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def get_embedding(text: str) -> list[float] | None:
    """Embed a single text chunk. Returns None on failure."""
    try:
        resp = requests.post(OLLAMA_URL, json={"model": MODEL, "input": text}, timeout=EMBED_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        return None
    except Exception as e:
        return None


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars:
            if current:
                chunks.append(current.strip())
            current = para
            if len(current) > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", current)
                current = ""
                for s in sentences:
                    if len(current) + len(s) + 1 > max_chars:
                        if current:
                            chunks.append(current.strip())
                        current = s
                    else:
                        current += " " + s if current else s
        else:
            current += "\n\n" + para if current else para
    if current:
        chunks.append(current.strip())
    return chunks


def push_points(points: list) -> None:
    resp = requests.put(QDRANT_URL, json={"points": points}, timeout=30)
    resp.raise_for_status()


def ingest_file(path: Path, ftype: str, date_str: str, state: dict, force: bool) -> int:
    """Ingest a single file. Returns number of points pushed."""
    if not path.exists():
        return 0

    fhash = file_hash(path)
    key = str(path.relative_to(Path.home()))

    if not force and state.get(key) == fhash:
        return 0  # unchanged

    content = path.read_text()
    if len(content.strip()) < 50:
        return 0

    chunks = chunk_text(content)
    if not chunks:
        return 0

    print(f"   → {len(chunks)} chunk(s) to embed...", end="", flush=True)

    embeddings = []
    failed = 0
    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk)
        if emb is None:
            failed += 1
            continue
        embeddings.append((chunk, emb))
        if (i + 1) % 5 == 0 or i == len(chunks) - 1:
            print(f" {i+1}/{len(chunks)}", end="", flush=True)

    if failed > 0:
        print(f"  ({failed} failed)")
    else:
        print("  ✓")

    if not embeddings:
        return 0

    ts = date_str + "T00:00:00" if re.match(r"\d{4}-\d{2}-\d{2}", date_str) else datetime.utcnow().isoformat() + "Z"

    points = []
    for i, (chunk, emb) in enumerate(embeddings, 1):
        points.append({
            "id": str(uuid.uuid4()),
            "vector": emb,
            "payload": {
                "content": chunk,
                "type": ftype,
                "importance": 8 if ftype.startswith("curated") else 7,
                "tags": [ftype.replace("_", "-")],
                "source": str(path.relative_to(Path.home())) if path.is_relative_to(Path.home()) else str(path),
                "context": f"chunk {i}/{len(chunks)}" if len(chunks) > 1 else "full",
                "timestamp": ts,
                "char_count": len(chunk),
            },
        })

    # Batch push to Qdrant
    batch_size = 16
    total_pushed = 0
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        try:
            push_points(batch)
            total_pushed += len(batch)
        except Exception as e:
            print(f"   → Qdrant push failed: {e}")
            break

    if total_pushed == len(points):
        state[key] = fhash
        save_state(state)

    return total_pushed


def main():
    parser = argparse.ArgumentParser(description="Sync memory files to Memory Node Qdrant via qwen3-embedding")
    parser.add_argument("--force", action="store_true", help="Re-process all files regardless of state")
    args = parser.parse_args()

    state = load_state()
    total_points = 0
    files_processed = 0

    print(f"📋 Memory sync (qwen3-embedding) started at {datetime.now().isoformat()}")
    print(f"   Target: {BASE_QDRANT_URL} / collection: vire_memory")
    print(f"   Embedding: {MODEL} via {BASE_OLLAMA_URL}")
    print(f"   Max chunk: {MAX_CHUNK_CHARS} chars (~100 words, ~{EMBED_TIMEOUT}s timeout)")
    print(f"   Force mode: {args.force}")
    print()

    # ─── Daily logs ──────────────────────────────────────
    if MEMORY_DIR.exists():
        daily_files = [f for f in sorted(os.listdir(MEMORY_DIR))
                       if f.endswith(".md") and not f.startswith(".")]
        print(f"📝 Scanning {len(daily_files)} daily log(s)...")
        for fname in daily_files:
            fpath = MEMORY_DIR / fname
            if fpath.stat().st_size < 200:
                continue
            date_match = re.match(r"(\d{4}-\d{2}-\d{2})", fname)
            date_clean = date_match.group(1) if date_match else fname.replace(".md", "")

            pushed = ingest_file(fpath, "daily_log", date_clean, state, args.force)
            if pushed > 0:
                files_processed += 1
                print(f"   ✅ {fname} → {pushed} point(s)")
            elif args.force:
                print(f"   🟡 {fname} — no change")
            total_points += pushed
    else:
        print(f"⚠️ Memory directory not found: {MEMORY_DIR}")

    print()

    # ─── Curated files ───────────────────────────────────
    print(f"📁 Scanning {len(CURATED_FILES)} curated file(s)...")
    for fname, ftype in CURATED_FILES:
        fpath = WORKSPACE_DIR / fname
        pushed = ingest_file(fpath, ftype, "curated", state, args.force)
        if pushed > 0:
            files_processed += 1
            print(f"   ✅ {fname} → {pushed} point(s)")
        elif args.force or fpath.exists():
            print(f"   🟡 {fname} — no change" if not pushed else f"   {fname} — skipped")
        total_points += pushed

    # ─── Summary ─────────────────────────────────────────
    print()
    if total_points == 0:
        print("🟡 No new or changed files to ingest.")
    else:
        print(f"{'=' * 55}")
        print(f"✅ Synced {total_points} point(s) from {files_processed} file(s)")
        print(f"{'=' * 55}")

    # Verify collection count
    try:
        info = requests.get(BASE_QDRANT_URL + "/collections/vire_memory", timeout=10).json()
        count = info["result"]["points_count"]
        print(f"📊 vire_memory total: {count} points")
    except Exception as e:
        print(f"⚠️ Could not verify collection count: {e}")


if __name__ == "__main__":
    main()
