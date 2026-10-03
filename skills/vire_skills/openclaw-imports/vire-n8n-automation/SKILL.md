---
name: vire-n8n-automation
description: "Use when building, triggering, or debugging optional n8n workflows through N8N_URL."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [n8n, automation, workflows, webhooks]
    related_skills: [vire, vire-shopify-management, vire-facebook-instagram, vire-gmail]
---

# Vire — N8N Workflow Automation

**Access**: Set `N8N_URL`; the single-computer default is `http://127.0.0.1:5678`.
**Config**: Store n8n credentials privately and enable only workflows you have reviewed.

## Trigger N8N Workflow via API
```bash
N8N_API_KEY=$(cat ~/.config/hermes-realm/secrets/n8n.env | grep N8N_API_KEY | cut -d= -f2)

curl -s -X POST "$N8N_URL/api/v1/workflows/<workflow-id>/activate" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

## Core Workflows to Build

- `shopify-order-notify` — New order → Gmail notification + Slack/Discord
- `meta-scheduler` — Read scheduled posts → publish to FB/IG at set times
- `tiktok-scheduler` — Queue TikTok uploads
- `inventory-alert` — Low stock → email alert
- `gmail-autoresponder` — Auto-reply customer emails
- `content-pipeline` — New video file detected → encode → thumbnail → schedule post

For the Shopify-specific workflow library (daily reports, order processor, inventory monitor, fulfillment tracker), see the `vire-shopify-management` skill.

## Trigger Webhook
```bash
curl -s -X POST "$N8N_URL/webhook/<webhook-id>" \
  -H "Content-Type: application/json" \
  -d '{"action":"post_now","platform":"instagram","asset":"/path/to/image.jpg"}'
```

## Node placement rule

N8N should not be the primary bridge for primary host-local Redis/voice/Hailo/audio state — Pi-local telemetry stays Pi-local (see `references/realm-dashboard-monitoring.md`).
