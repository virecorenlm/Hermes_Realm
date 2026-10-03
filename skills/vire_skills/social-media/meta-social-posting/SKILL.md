---
name: meta-social-posting
title: Meta / Facebook Page Posting Automation
description: Build, test, and operate Facebook Page posting automation using Meta Graph API, Page access tokens, safe secret handling, dry-run posts, and cron/agent workflows.
version: 1.0.0
author: Vire
created_by: agent
---

# Meta / Facebook Page Posting Automation

## When to use

Use when the operator wants to:
- test a Facebook/Meta/Instagram access token stored under `~/.config/hermes-realm/secrets/`
- post or schedule content to a Facebook Page or Instagram business/professional account for a business
- turn existing Hermes cron outputs such as fishing forecasts, bait tips, and weather alerts into social posts
- wire Meta posting into Hermes cron jobs, agents, n8n, Shopify, or app promotion
- debug Graph API permission errors such as `OAuthException code=200`
- decide whether to use n8n's Facebook node, n8n HTTP Request node, or direct Hermes/Python scripts

## Core rule

**Do not print or paste access tokens into chat.** Read tokens from a local secret file, redact them in output, and use token-check calls that only print identity, permissions, page IDs, and error messages.

Preferred secret files:

```bash
~/.config/hermes-realm/secrets/facebook.env
~/.config/hermes-realm/secrets/instagram.env
chmod 600 ~/.config/hermes-realm/secrets/*.env
```

Common Facebook keys:

```bash
facebook_access_token="..."          # user token or temporary token
facebook_page_id="..."               # Page ID
facebook_page_access_token="..."     # preferred token for publishing
```

Accept uppercase aliases if existing scripts use them:

```bash
FACEBOOK_ACCESS_TOKEN
META_ACCESS_TOKEN
FACEBOOK_PAGE_ID
META_PAGE_ID
FACEBOOK_PAGE_ACCESS_TOKEN
META_PAGE_ACCESS_TOKEN
```

Common Instagram keys:

```bash
instagram_access_token="..."          # Meta Graph user token with Instagram scopes
instagram_user_id="..."               # Instagram business/professional user ID
```

Accept uppercase aliases:

```bash
INSTAGRAM_ACCESS_TOKEN
IG_ACCESS_TOKEN
INSTAGRAM_USER_ID
IG_USER_ID
```

Use the operator-configured store URL in captions. Review generated text before posting.

Detailed Instagram image-posting recipe: `references/instagram-graph-image-posting.md`.

## Safe workflow

1. **Locate the secret file without displaying secrets.**
   - Print file existence, mode, size, and variable names only.
   - If mode is wider than `600`, fix it with `chmod 600`.

2. **Check the token before posting.**
   - `GET /me?fields=id,name` verifies the token is valid.
   - `GET /me/permissions` shows granted permissions.
   - `GET /me/accounts?fields=id,name,tasks,perms,category` checks whether the token can see managed Pages.
   - If the Page is under Business Manager, also check `/me/businesses` and `/{business-id}/owned_pages`.

3. **Draft the post first.**
   - Write the candidate post to a local draft file such as `post-draft.txt`.
   - Keep draft generation separate from publishing.

4. **Only publish with a Page-capable token.**
   - Use `POST /{page-id}/feed` with a **Page access token** where possible.
   - Required permissions for Page posting commonly include:
     - `pages_show_list`
     - `pages_read_engagement`
     - `pages_manage_posts`
   - The user must have sufficient admin/business permission on the Page.

5. **Capture exact API errors.**
   - Report HTTP status, `error.type`, `error.code`, `error_subcode`, and message.
   - Do not summarize away permission details; they tell the operator exactly what to fix in Meta Developer settings.

## Instagram Business publishing

Use this section when the operator wants to post to Instagram from a token under `~/.config/hermes-realm/secrets/`, from a fishing-content directory, or from cron-generated fishing/weather/tip output.

Key points:
- A Meta Graph USER token may work for Instagram Business publishing even if `https://graph.instagram.com/me` says `Invalid OAuth access token - Cannot parse access token`. That Basic Display endpoint is the wrong API for Meta Graph Business tokens.
- Verify Instagram Business access through `https://graph.facebook.com/vXX.X/{ig-user-id}` and `debug_token` instead.
- Expected scopes include `instagram_basic` and `instagram_content_publish`.
- Instagram Graph posting is **not** text-only: create a media container from a publicly reachable `image_url` or video URL, poll until `FINISHED`, then publish the container.
- Local files must be cropped/exported and uploaded somewhere public before `POST /{ig-user-id}/media`; never fabricate a public URL if upload fails.
- For content directories, avoid screenshots, logos, and social-icon PNGs; prefer real fishing photos and keep a used-image ledger so scheduled jobs rotate content.
- For cron-driven Instagram posts based on other cron outputs, schedule the Instagram job a few minutes after the source jobs and use `context_from` so the completed upstream output is available.

See `references/instagram-graph-auto-posting.md` for the concrete checked workflow, curl upload pattern, API sequence, and cron prompt pattern.

## Instagram Graph image publishing

Instagram business/professional publishing through Meta Graph uses the Facebook Graph host, not the Basic Display host.

Use this flow for image posts:
1. Read the Meta Graph user token from `~/.config/hermes-realm/secrets/instagram.env` without printing it.
2. Verify with `GET graph.facebook.com/vXX.X/me`, `debug_token`, and `GET /{ig_user_id}`.
3. Choose/crop a real image to an Instagram-safe JPEG. Meta cannot publish a local file path directly.
4. Upload the image to a public HTTPS URL.
5. `POST /{ig_user_id}/media` with `image_url`, `caption`, and `access_token`.
6. Poll `/{creation_id}?fields=status_code,status` until `FINISHED`.
7. `POST /{ig_user_id}/media_publish` with `creation_id`.
8. Verify with `GET /{media_id}?fields=id,permalink,media_type,timestamp`.

Pitfalls:
- `graph.instagram.com/me` can reject a valid Meta Graph token with “Cannot parse access token”; use `graph.facebook.com/vXX.X/{ig_user_id}` for these tokens.
- Instagram does not publish text-only feed posts via Graph; provide an image/video/reel container.
- For cron-driven posts, schedule the poster a few minutes after the report generator and inject upstream output with `context_from`.
- Strip Hermes scheduler boilerplate before turning a cron response into a caption.
- Keep a used-image ledger if selecting from a directory to avoid repetitive posts.

See `references/instagram-graph-image-posting.md` for the the configured store recipe.

## n8n guidance

If n8n's Facebook Graph node only offers an older Graph API version than Meta's current version, do **not** update n8n just for that.

Safer options:
- use n8n's generic HTTP Request node to call `https://graph.facebook.com/vXX.X/{page-id}/feed`; or
- use a direct Hermes/Python script and schedule it with Hermes cron.

Only update self-hosted n8n after a backup of database, `.env`, `N8N_ENCRYPTION_KEY`, docker compose file, and data volume.

## Common permission outcomes

### Token valid but no pages returned

Symptoms:

```text
/me status: 200
/me/accounts status: 200
Pages: []
granted permissions: business_management, public_profile
```

Meaning:
- the token is real, but it is not enough to list/manage Pages.
- request `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts`.
- confirm the Facebook account has Page admin/business access.

### Posting returns OAuthException code 200

Typical message:

```text
(#200) ... If posting to a page, requires both pages_read_engagement and pages_manage_posts as an admin with sufficient administrative permission
```

Meaning:
- the endpoint and Page ID may be correct;
- the token lacks required Page permissions or is not a Page access token;
- generate/exchange a token with the Page permissions and retrieve the Page token from `/me/accounts` or Business Manager tooling.

## Reusable helper pattern

Prefer a helper script with explicit modes:

```bash
meta_facebook_poster.py --check
meta_facebook_poster.py --post --message-file /tmp/post.txt
```

The helper should:
- load `~/.config/hermes-realm/secrets/facebook.env`
- never print tokens
- show granted permissions and discovered Pages
- refuse to post if `facebook_page_id` or `facebook_page_access_token` is missing
- print the post ID on success

See `references/facebook-page-token-permissions.md` for a concrete session-derived permission/debug recipe.

## Pitfalls

- User access tokens are not always enough to publish to Pages.
- Business Manager can show owned Pages even when `/me/accounts` returns no page access token.
- A discovered Page ID does not imply permission to post.
- n8n node version dropdowns are not blockers if the generic HTTP Request node or direct Python can call the desired Graph version.
- Do not treat a successful `/me` response as a successful posting setup; check Page visibility and Page posting permissions separately.
