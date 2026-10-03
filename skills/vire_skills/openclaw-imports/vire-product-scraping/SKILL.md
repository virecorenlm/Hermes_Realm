---
name: vire-product-scraping
description: "Use when collecting fishing-lure product data from the operator's own Shopify store and vendor reference pages for training data, labels, or product metadata. Own-store-first rule; vendor content is reference-only, never copied."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [scraping, shopify, training-data, fishing, product-data]
    related_skills: [vire, vire-shopify-management, vire-lure-photo-pipeline]
---

# Vire — Fishing Vendor + Shopify Product Scraping

Collect fishing-lure product data from the operator's own Shopify store and vendor pages (reference-only) for training data, labels, or product metadata.

## Rules

- Safe sources: the configured store's product data and licensed inventory photos, followed by vendor pages used only for factual reference.
- Maintain a vendor list chosen by the operator; do not infer rights to copy catalog text or images.
- Normalized JSONL output with `source_type`, `brand`, `model`, `lure_type`, `colors`, `condition`, `price`, `description_summary`, `image_paths`, `rights_note`.
- **Important:** always scrape the operator's own store first; vendor content is reference-only.
