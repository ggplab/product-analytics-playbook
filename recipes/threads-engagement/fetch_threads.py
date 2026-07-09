"""
Pull YOUR OWN Threads posts + insights into data/threads_posts.csv.

This replaces the synthetic generate_data.py with real data from your account,
producing the exact same CSV shape so analyze.py runs unchanged:

    post_id, published_at, track, theme, views, likes, replies, reposts, quotes

Prerequisites (see connect-meta.md for the full walk-through):
  - A Meta app with the Threads use case, permissions threads_basic +
    threads_manage_insights, and yourself added as a Threads Tester.
  - A long-lived access token and your numeric user id, in environment vars:
        export THREADS_ACCESS_TOKEN="THQVJ..."
        export THREADS_USER_ID="17841400000000000"

Note on `track` / `theme`: the API returns metrics, not editorial labels. Your
content pillar is YOUR call, so those two columns come out as "untagged" here —
tag them (by hand, a keyword map, or an LLM pass) before the per-pillar chart in
analyze.py becomes meaningful. Everything else works immediately.

Uses only the Python standard library — no third-party HTTP client needed.

Run:
    python fetch_threads.py
    -> writes data/threads_posts.csv
"""

import csv
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

API = "https://graph.threads.net/v1.0"
BASE_DIR = Path(__file__).parent
OUT_PATH = BASE_DIR / "data" / "threads_posts.csv"

TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")
USER_ID = os.environ.get("THREADS_USER_ID")


def http_json(url):
    req = Request(url, headers={"Accept": "application/json",
                                "User-Agent": "threads-engagement-recipe/1.0"})
    try:
        with urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return {"_http_error": e.code, **json.loads(body)}
        except Exception:
            return {"_http_error": e.code, "_raw": body}


def fetch_posts(limit=100, max_pages=25):
    """Page through the account's own posts (newest first)."""
    url = f"{API}/me/threads?" + urlencode({
        "fields": "id,timestamp,permalink,media_type,is_quote_post,is_reply",
        "limit": limit,
        "access_token": TOKEN,
    })
    posts = []
    for _ in range(max_pages):
        data = http_json(url)
        if "error" in data or "_http_error" in data:
            sys.exit(f"Error fetching posts: {data}")
        posts.extend(data.get("data", []))
        nxt = (data.get("paging") or {}).get("next")
        if not nxt:
            break
        url = nxt
        time.sleep(0.2)
    return posts


def fetch_insights(post_id):
    """Per-post metrics. Missing metrics come back as 0."""
    url = f"{API}/{post_id}/insights?" + urlencode({
        "metric": "views,likes,replies,reposts,quotes",
        "access_token": TOKEN,
    })
    data = http_json(url)
    out = {"views": 0, "likes": 0, "replies": 0, "reposts": 0, "quotes": 0}
    if "_http_error" in data or "error" in data:
        # A permission slip (e.g. losing threads_manage_insights, error code 10)
        # silently zeros insights — surface it instead of writing junk.
        print(f"  ! insights unavailable for {post_id}: {data}", file=sys.stderr)
        return out
    for m in data.get("data", []):
        name = m.get("name")
        values = m.get("values") or []
        if values:
            out[name] = values[0].get("value", 0) or 0
        elif isinstance(m.get("total_value"), dict):
            out[name] = m["total_value"].get("value", 0) or 0
    return out


def main():
    if not TOKEN or not USER_ID:
        sys.exit("Set THREADS_ACCESS_TOKEN and THREADS_USER_ID (see connect-meta.md).")

    posts = fetch_posts()
    # Keep original posts only; replies to others aren't part of your reach funnel.
    posts = [p for p in posts if not p.get("is_reply")]
    print(f"Fetched {len(posts)} original posts. Pulling insights...")

    rows = []
    for i, p in enumerate(posts, 1):
        ins = fetch_insights(p["id"])
        rows.append({
            "post_id": p["id"],
            "published_at": (p.get("timestamp") or "").replace("T", " ")[:19],
            "track": "untagged",
            "theme": "untagged",
            **ins,
        })
        if i % 25 == 0:
            print(f"  {i}/{len(posts)}")
        time.sleep(0.15)

    OUT_PATH.parent.mkdir(exist_ok=True)
    fields = ["post_id", "published_at", "track", "theme",
              "views", "likes", "replies", "reposts", "quotes"]
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"\nWritten: {OUT_PATH}  ({len(rows)} posts)")
    print("Next: tag the `theme`/`track` columns, then run  python analyze.py")


if __name__ == "__main__":
    main()
