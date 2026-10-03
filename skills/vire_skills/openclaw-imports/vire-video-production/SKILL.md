---
name: vire-video-production
description: "Use when recording or editing video with OBS and FFmpeg on a configured computer."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [video, obs, ffmpeg, editing]
    related_skills: [vire, vire-reels-pipeline, vire-graphic-design]
---

# Video Content Creation

## Record with OBS

Run OBS on a computer with a supported desktop and capture devices.
```bash
obs --startrecording --scene "BaitTackle-Scene"
# Stop from OBS UI, or via configured automation.
```

## Trim & Export Clip
```bash
# scripts/trim-clip.sh <input> <start> <duration> <output>
ffmpeg -i "$1" -ss "$2" -t "$3" -c:v libx264 -c:a aac -preset fast "$4"
```

## Add Watermark/Logo
```bash
ffmpeg -i input.mp4 -i assets/vire-logo.png \
  -filter_complex "overlay=W-w-10:H-h-10" \
  -c:a copy output-branded.mp4
```

## Create Vertical Short (9:16) from Horizontal
```bash
ffmpeg -i input.mp4 \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" \
  -c:a copy output-vertical.mp4
```

## Generate Thumbnail
```bash
ffmpeg -i input.mp4 -ss 00:00:03 -vframes 1 thumbnail.jpg
```

## Node placement

Use FFmpeg on any supported machine; select capture and rendering tools based on available hardware.
