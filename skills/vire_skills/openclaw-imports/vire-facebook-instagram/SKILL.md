---
name: vire-facebook-instagram
description: "Use when posting to the configured store Facebook Page or Instagram business account via the Meta Graph API: page feed posts, IG media container upload/publish, and N8N-scheduled posts."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [facebook, instagram, meta, graph-api, social-media]
    related_skills: [vire, vire-content-strategy, vire-n8n-automation, meta-social-posting]
---

# Vire — Social Media: Facebook & Instagram

**Auth**: Facebook Graph API via long-lived token stored in `~/.config/hermes-realm/secrets/meta.env`
```bash
META_ACCESS_TOKEN=<long-lived-token>
META_PAGE_ID=<facebook-page-id>
META_IG_ACCOUNT_ID=<instagram-business-account-id>
```

## Post to Facebook Page
```bash
source ~/.config/hermes-realm/secrets/meta.env
curl -s -X POST \
  "https://graph.facebook.com/v19.0/$META_PAGE_ID/feed" \
  -d "message=<your message>" \
  -d "access_token=$META_ACCESS_TOKEN"
```

## Post Image to Instagram
```bash
# Step 1: Upload media container
source ~/.config/hermes-realm/secrets/meta.env
CONTAINER=$(curl -s -X POST \
  "https://graph.facebook.com/v19.0/$META_IG_ACCOUNT_ID/media" \
  -d "image_url=<PUBLIC_IMAGE_URL>" \
  -d "caption=<caption with #hashtags>" \
  -d "access_token=$META_ACCESS_TOKEN" | jq -r '.id')

# Step 2: Publish
curl -s -X POST \
  "https://graph.facebook.com/v19.0/$META_IG_ACCOUNT_ID/media_publish" \
  -d "creation_id=$CONTAINER" \
  -d "access_token=$META_ACCESS_TOKEN"
```

## Schedule Posts

Use N8N workflow `meta-scheduler` — see the `vire-n8n-automation` skill.

## Guardrails

- Never post to social media without content existing in `~/.config/hermes-realm/content/scheduled/`.
- Never expose tokens in logs, stdout, or chat replies.
