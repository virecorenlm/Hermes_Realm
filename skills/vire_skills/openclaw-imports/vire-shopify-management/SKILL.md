---
name: vire-shopify-management
description: "Use when managing the configured store Shopify store: listing products, updating prices, checking inventory, monitoring orders, and running the advanced N8N-backed Shopify workflow library (daily reports, order processing, inventory alerts, fulfillment tracking)."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [shopify, ecommerce, n8n, orders, inventory]
    related_skills: [vire, vire-n8n-automation, vire-lure-photo-pipeline, vire-product-scraping]
---

# Vire — Shopify E-Commerce Management

**Store**: `example-store.myshopify.com`

## Authentication

Store API credentials in `~/.config/hermes-realm/secrets/shopify.env`:
```bash
SHOPIFY_STORE=example-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=<token>
SHOPIFY_API_VERSION=<supported-api-version>
```

Load before any Shopify operation:
```bash
source ~/.config/hermes-realm/secrets/shopify.env
```

## List Products
```bash
curl -s -H "X-Shopify-Access-Token: $SHOPIFY_ACCESS_TOKEN" \
  "https://$SHOPIFY_STORE/admin/api/$SHOPIFY_API_VERSION/products.json?limit=50" \
  | jq '.products[] | {id, title, status, variants: [.variants[] | {sku, price, inventory_quantity}]}'
```

## Update Product Price
```bash
# scripts/shopify-update-price.sh <product_id> <variant_id> <new_price>
source ~/.config/hermes-realm/secrets/shopify.env
curl -s -X PUT \
  -H "X-Shopify-Access-Token: $SHOPIFY_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"variant\":{\"id\":$2,\"price\":\"$3\"}}" \
  "https://$SHOPIFY_STORE/admin/api/$SHOPIFY_API_VERSION/variants/$2.json"
```

## Check Inventory
```bash
curl -s -H "X-Shopify-Access-Token: $SHOPIFY_ACCESS_TOKEN" \
  "https://$SHOPIFY_STORE/admin/api/$SHOPIFY_API_VERSION/inventory_levels.json?location_ids=<location_id>" \
  | jq '.inventory_levels[] | select(.available < 5) | {inventory_item_id, available}'
```

## Create/Update Product

Use `scripts/shopify-upsert-product.py` — see scripts folder.

## Monitor Orders
```bash
curl -s -H "X-Shopify-Access-Token: $SHOPIFY_ACCESS_TOKEN" \
  "https://$SHOPIFY_STORE/admin/api/$SHOPIFY_API_VERSION/orders.json?status=open&limit=25" \
  | jq '.orders[] | {id, name, email, total_price, fulfillment_status, created_at}'
```

---

# Advanced Shopify Operations

Use a store and API version you configure. The companion workflow files below are examples of possible integrations and are not shipped in this repository.

## Workflow Library (N8N)

| File | Name | Trigger | What it does |
|------|------|---------|-------------|
| `shopify-daily-report.json` | Daily Sales Report | 8AM cron | Revenue, orders, top products → Gmail |
| `shopify-order-processor.json` | Order Processor | Webhook + 5min poll | New orders → log + Gmail alert |
| `shopify-inventory-monitor.json` | Inventory Monitor | Hourly cron | Low stock detection → Gmail alert |
| `shopify-product-sync.json` | Product Sync | 6-hour cron | Sync full product catalog |
| `shopify-fulfillment-tracker.json` | Fulfillment Tracker | 30min cron | Unfulfilled orders aging report |
| `shopify-weekly-report.json` | Weekly Report | Monday 7AM | Full weekly business summary |

## Credential Setup in N8N

In N8N UI → Credentials → New:
- **Type**: Header Auth
- **Name**: `ShopifyVire`
- **Header**: `X-Shopify-Access-Token`
- **Value**: `<your shopify access token>`

## Scripts

- `scripts/import-shopify-workflows.sh` — Import N8N workflows
- `scripts/test-shopify-connection.sh` — Verify Shopify API connectivity
- `assets/workflows/shopify-*.json` — Pre-built N8N workflow templates

## Guardrails (Shopify)

- Never PUT/POST to Shopify without explicit data validation in the Code node first.
- Never update product prices or inventory in bulk without a confirmation step.
- All Shopify API calls must go through N8N credentials — key never appears in Code nodes.
- Rate limit: add 600ms delay between batch API calls.
- All errors must be caught, logged, and emailed.
- Always verify Shopify API response before reporting success.
