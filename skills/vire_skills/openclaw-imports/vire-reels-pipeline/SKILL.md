---
name: vire-reels-pipeline
description: "Use when producing short-form video (Reels/TikToks/Shorts): the raw → working → ready-to-post folder flow, content-type scripts, platform video specs, and reels guardrails (versioning, captions, cleanup)."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [reels, tiktok, shorts, video, pipeline, ffmpeg]
    related_skills: [vire, vire-video-production, vire-tiktok, vire-content-strategy]
---

# Vire — Short-Form Video / Reels Pipeline

Vire's short-form video production pipeline. Takes raw footage or a content brief, and outputs upload-ready Reels/TikToks. For full detail, see `references/content-guide.md`.

## Output Folder Structure

```
~/.config/hermes-realm/content/
├── raw/                     ← Drop raw footage here
├── working/                 ← Intermediate files (auto-cleaned)
├── ready-to-post/           ← ✅ UPLOAD FROM HERE
│   ├── YYYY-MM-DD_[platform]_[topic]_v1_vertical.mp4
│   ├── YYYY-MM-DD_[platform]_[topic]_v1_thumb.jpg
│   └── YYYY-MM-DD_[platform]_[topic]_v1_caption.txt
└── posted/                  ← Move here after you upload
```

## Content Types

| Type | Script | What it needs |
|------|--------|--------------|
| Product Spotlight Reel | `scripts/make-product-reel.sh` | Product images + name + price |
| Fishing Tip Reel | `scripts/make-tip-reel.sh` | Tip text + B-roll clip |
| Raw Footage → Reel | `scripts/make-reel-from-footage.sh` | Raw .mp4 file |
| Text-Only / Talking Head | `scripts/make-text-reel.py` | Script text (renders as cards) |
| Slideshow Reel | `scripts/make-slideshow-reel.sh` | 3–8 images + music |

## Video Specs (Platform Standards)

| Platform | Resolution | Aspect | Max Length | Format |
|---------|-----------|--------|-----------|--------|
| TikTok | 1080×1920 | 9:16 | 60s (best: 15-30s) | MP4 H.264 |
| Instagram Reels | 1080×1920 | 9:16 | 90s (best: 15-30s) | MP4 H.264 |
| YouTube Shorts | 1080×1920 | 9:16 | 60s | MP4 H.264 |

## Guardrails (Reels)

- Never overwrite files in `ready-to-post/` — always increment version suffix (`_v1`, `_v2`)
- Always generate caption file alongside every video
- Clean `working/` after successful export (keep `raw/` untouched)
- If FFmpeg fails mid-encode, delete partial output and log failure
- For media sorting/intake tools, never scan a plain directory that is intended to be an SMB mount; first verify it is mounted (`mountpoint -q` or `Path(...).is_mount()`)
