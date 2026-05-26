"""Phase 1 — scrape top posts from a meme subreddit and save metadata + media."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import praw
import requests
from dotenv import load_dotenv

load_dotenv()

SUBREDDIT = os.getenv("SUBREDDIT", "memes")
TIME_FILTER = os.getenv("TIME_FILTER", "year")
LIMIT = int(os.getenv("LIMIT", "1000"))

OUT_DIR = Path("data")
IMG_DIR = OUT_DIR / "images"
META_FILE = OUT_DIR / "memes.json"
IMG_DIR.mkdir(parents=True, exist_ok=True)

VALID_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

reddit = praw.Reddit(
    client_id=os.environ["REDDIT_CLIENT_ID"],
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    user_agent=os.environ.get("REDDIT_USER_AGENT", "memeradar/0.1"),
)


def safe_ext(url: str) -> str | None:
    path = urlparse(url).path.lower()
    for ext in VALID_EXT:
        if path.endswith(ext):
            return ext
    return None


def resolve_direct_url(post) -> str | None:
    url = post.url
    if safe_ext(url):
        return url
    if "i.redd.it" in url or "i.imgur.com" in url:
        return url
    if hasattr(post, "preview"):
        try:
            return post.preview["images"][0]["source"]["url"].replace("&amp;", "&")
        except (KeyError, IndexError, AttributeError):
            return None
    return None


def slug(text: str, n: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", text)[:n].strip("_")
    return s or "untitled"


def download(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "memeradar/0.1"})
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"  download failed: {e}")
        return False


def main():
    sub = reddit.subreddit(SUBREDDIT)
    records = []
    seen = set()

    for i, post in enumerate(sub.top(time_filter=TIME_FILTER, limit=LIMIT)):
        if post.id in seen or post.over_18 or post.is_self:
            continue
        seen.add(post.id)

        url = resolve_direct_url(post)
        if not url:
            continue
        ext = safe_ext(url) or ".jpg"
        fname = f"{post.id}_{slug(post.title, 40)}{ext}"
        fpath = IMG_DIR / fname

        if not fpath.exists():
            if not download(url, fpath):
                continue
            time.sleep(0.3)  # gentle on Reddit's CDN

        records.append({
            "id": post.id,
            "image_path": str(fpath.resolve()),
            "post_title": post.title,
            "upvotes": post.score,
            "num_comments": post.num_comments,
            "meme_template_name": (post.link_flair_text or "").strip() or None,
            "permalink": f"https://reddit.com{post.permalink}",
            "created_utc": post.created_utc,
            "source_url": url,
        })

        if (i + 1) % 25 == 0:
            META_FILE.write_text(json.dumps(records, indent=2))
            print(f"[{len(records)}] checkpointed")

    META_FILE.write_text(json.dumps(records, indent=2))
    print(f"done. {len(records)} memes -> {META_FILE}")


if __name__ == "__main__":
    main()
