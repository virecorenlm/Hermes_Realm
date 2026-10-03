---
name: vire-media-sorting
description: "Use when building or running safe copy-only media sorting pipelines over mounted SMB/CIFS shares: dry-run/live modes, SQLite indexing, modular detectors (Hailo/OpenCV/CLIP), and mount-guard pitfalls."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [media, sorting, smb, hailo, clip, dry-run, safety]
    related_skills: [vire, vire-reels-pipeline]
---

# Vire — Media Content Sorting Pipelines

Build safe copy-only media sorting pipelines over mounted shares (SMB/CIFS) with dry-run/live modes, SQLite indexing, and modular detectors (Hailo/OpenCV/CLIP).

## Core safety

- Dry-run default; copy-only (never delete originals).
- No overwrites (`_copy1`, `_copy2`).
- Credentials in chmod-600 files outside the project tree.

## Project shape

`config.yaml`, `scan.py`, `media_index.py`, `frame_extract.py`, `scoring.py`, `copy_manager.py`, `detectors/hailo_detector.py`, `detectors/fallback_detector.py`.

## Critical pitfalls

- Guard unmounted paths (`path.is_mount()` before scan).
- Score keywords against the path relative to the mount, not the absolute path (a mountpoint name may contain a target keyword).
- Report `hailo_runtime_present` and `hailo_detections_total` separately from `hailortcli scan`.
- Hailo CLIP gotchas: text HEF may need pre-token-embedded tensors; image output `UINT16` requires dequantization before cosine similarity.
