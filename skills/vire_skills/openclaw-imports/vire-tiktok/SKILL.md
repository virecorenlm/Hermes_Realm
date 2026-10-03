---
name: vire-tiktok
description: "Use when uploading or scheduling TikTok videos for the configured store via the TikTok Content Posting API: init upload, chunked file PUT, and the wrapped tiktok-post.sh script."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [tiktok, social-media, video, content-posting-api]
    related_skills: [vire, vire-content-strategy, vire-reels-pipeline]
---

# Vire — Social Media: TikTok

**Auth**: TikTok Content Posting API. Credentials in `~/.config/hermes-realm/secrets/tiktok.env`
```bash
TIKTOK_ACCESS_TOKEN=<token>
TIKTOK_OPEN_ID=<open_id>
```

## Upload Video to TikTok (Direct Post)
```bash
source ~/.config/hermes-realm/secrets/tiktok.env
# Step 1: Init upload
INIT=$(curl -s -X POST \
  "https://open.tiktokapis.com/v2/post/publish/video/init/" \
  -H "Authorization: Bearer $TIKTOK_ACCESS_TOKEN" \
  -H "Content-Type: application/json; charset=UTF-8" \
  -d '{
    "post_info": {"title":"<title>","privacy_level":"PUBLIC_TO_EVERYONE"},
    "source_info": {"source":"FILE_UPLOAD","video_size":<bytes>,"chunk_size":<bytes>,"total_chunk_count":1}
  }')

PUBLISH_ID=$(echo $INIT | jq -r '.data.publish_id')
UPLOAD_URL=$(echo $INIT | jq -r '.data.upload_url')

# Step 2: Upload file
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: video/mp4" \
  -H "Content-Range: bytes 0-<size-1>/<size>" \
  --data-binary @/path/to/video.mp4
```

Use `scripts/tiktok-post.sh <video_path> <title>` for a wrapped version.

## Scheduling

Queue TikTok uploads with the N8N workflow `tiktok-scheduler` — see the `vire-n8n-automation` skill.

## Guardrails

- Never post without content existing in `~/.config/hermes-realm/content/scheduled/`.
- Never expose tokens in logs, stdout, or chat replies.
