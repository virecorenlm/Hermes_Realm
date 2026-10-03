#!/usr/bin/env python3
"""Safe Facebook Page posting helper for a configured Page.

Reads secrets from the Realm config directory by default.
Never prints access tokens.

Expected env vars, any compatible names:
  facebook_access_token / FACEBOOK_ACCESS_TOKEN / META_ACCESS_TOKEN
  facebook_page_id / FACEBOOK_PAGE_ID / META_PAGE_ID          optional but needed to post
  facebook_page_access_token / FACEBOOK_PAGE_ACCESS_TOKEN     optional; preferred for posting
"""
from __future__ import annotations

import argparse
import os
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from realm_config import realm_path

GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v25.0")
DEFAULT_ENV = realm_path("secrets", "facebook.env")


def load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip().replace("export ", "")
        val = val.strip().strip('"').strip("'")
        data[key] = val
    return data


def first(env: dict[str, str], *names: str) -> str | None:
    for name in names:
        val = env.get(name)
        if val:
            return val
    return None


class GraphClient:
    def __init__(self, token: str):
        self.token = token

    def request(self, path: str, params: dict[str, str] | None = None, method: str = "GET") -> tuple[int | None, dict]:
        params = dict(params or {})
        params["access_token"] = self.token
        url = f"https://graph.facebook.com/{GRAPH_VERSION}{path}"
        body = None
        if method.upper() == "GET":
            url += "?" + urllib.parse.urlencode(params)
        else:
            body = urllib.parse.urlencode(params).encode()
        try:
            with urllib.request.urlopen(url, data=body, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode(errors="replace")
            try:
                data = json.loads(raw)
            except Exception:
                data = {"error": {"message": raw[:500], "type": "HTTPError"}}
            return exc.code, data
        except Exception as exc:
            return None, {"error": {"message": str(exc), "type": type(exc).__name__}}


def summarize_error(data: dict) -> str:
    err = data.get("error", {}) if isinstance(data, dict) else {}
    return f"{err.get('type', 'Error')} code={err.get('code', 'unknown')}: {err.get('message', data)}"


def check(env: dict[str, str]) -> int:
    user_token = first(env, "facebook_access_token", "FACEBOOK_ACCESS_TOKEN", "META_ACCESS_TOKEN", "META_PAGE_ACCESS_TOKEN")
    if not user_token:
        print("ERROR: no access token found in env file")
        return 2
    client = GraphClient(user_token)

    status, me = client.request("/me", {"fields": "id,name"})
    print(f"/me status: {status}")
    if "error" in me:
        print("/me error:", summarize_error(me))
        return 1
    print(f"token belongs to: {me.get('name')} ({me.get('id')})")

    status, perms = client.request("/me/permissions")
    granted = []
    if isinstance(perms, dict):
        granted = [p.get("permission") for p in perms.get("data", []) if p.get("status") == "granted"]
    print("granted permissions:", ", ".join(granted) if granted else "none detected")

    status, accounts = client.request("/me/accounts", {"fields": "id,name,tasks,perms,category"})
    print(f"/me/accounts status: {status}")
    if "error" in accounts:
        print("/me/accounts error:", summarize_error(accounts))
        return 1
    pages = accounts.get("data", []) if isinstance(accounts, dict) else []
    if not pages:
        print("No Facebook Pages returned. Need pages_show_list + pages_manage_posts and/or Page role access before posting to a business page.")
        return 3
    for page in pages:
        print(f"page: {page.get('name')} ({page.get('id')}) tasks={page.get('tasks') or page.get('perms')}")
    return 0


def post(env: dict[str, str], message: str) -> int:
    page_id = first(env, "facebook_page_id", "FACEBOOK_PAGE_ID", "META_PAGE_ID")
    token = first(env, "facebook_page_access_token", "FACEBOOK_PAGE_ACCESS_TOKEN", "META_PAGE_ACCESS_TOKEN")
    if not page_id:
        print(f"ERROR: page id missing. Add META_PAGE_ID to {DEFAULT_ENV}")
        return 2
    if not token:
        print(f"ERROR: page access token missing. Add META_PAGE_ACCESS_TOKEN to {DEFAULT_ENV}")
        return 2
    client = GraphClient(token)
    status, data = client.request(f"/{page_id}/feed", {"message": message}, method="POST")
    print(f"POST /{page_id}/feed status: {status}")
    if "error" in data:
        print("post error:", summarize_error(data))
        return 1
    print("posted id:", data.get("id"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or post to a Facebook Page via Graph API")
    parser.add_argument("--env", default=str(DEFAULT_ENV), help="env file path")
    parser.add_argument("--check", action="store_true", help="check token, permissions, and page visibility")
    parser.add_argument("--post", action="store_true", help="publish a post to the configured Page")
    parser.add_argument("--message-file", help="file containing post message")
    args = parser.parse_args()

    env = {**load_env(Path(args.env).expanduser()), **os.environ}
    if args.check or not args.post:
        code = check(env)
        if not args.post:
            return code
    if args.post:
        if not args.message_file:
            print("ERROR: --message-file required with --post")
            return 2
        message = Path(args.message_file).read_text(encoding="utf-8")
        return post(env, message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
