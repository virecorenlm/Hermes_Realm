---
name: vire-lure-photo-pipeline
description: "Use when automating lure-photo-to-Shopify-draft for the configured store: upload folder → n8n → Pi 5 vision/Hailo analysis → local LLM metadata → Shopify draft. Drafts only, never auto-publish."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [shopify, vision, hailo, drafts, pipeline, n8n]
    related_skills: [vire, vire-shopify-management, vire-product-scraping, vire-n8n-automation]
---

# Lure Photo to Shopify Draft Pipeline

Automate lure-photo-to-Shopify-draft for the configured store.

**Shopify store:** `example-store.myshopify.com`

## Architecture

Upload folder → optional n8n workflow → optional vision analysis → local model metadata draft → Shopify Admin API draft → operator review → publish.

## Rules

- Always create `status: draft`; never auto-publish.
- Tag AI-generated drafts: `ai-generated`, `needs-review`, `used-lure`.
- If vision confidence is low, set `needs_review=true`.
