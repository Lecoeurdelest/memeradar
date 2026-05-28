from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import praw
import requests

from backend import config


CHECKPOINT_INTERVAL = 25
MANIFEST_PATH = config.DATA_DIR / "memes.json"
IMAGES_DIR = config.DATA_DIR / "images"

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def load_manifest() -> list[dict]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return []


def save_manifest(entries: list[dict]) -> None:
    MANIFEST_PATH.write_text(json.dumps(entries, indent=2))


def safe_ext(url: str) -> str | None:
    path = urlparse(url).path.lower()
    for ext in VALID_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return None


def resolve_image_url(submission) -> str | None:
    url = submission.url

    if safe_ext(url):
        return url

    parsed = urlparse(url)

    if parsed.hostname in ("i.redd.it", "i.imgur.com"):
        return url

    if parsed.hostname in ("imgur.com",):
        imgur_id = Path(parsed.path).stem
        return f"https://i.imgur.com/{imgur_id}.jpg"

    if hasattr(submission, "preview") and submission.preview:
        try:
            return submission.preview["images"][0]["source"]["url"].replace("&amp;", "&")
        except (KeyError, IndexError, AttributeError):
            return None

    return None


def is_valid_submission(submission) -> bool:
    if submission.over_18:
        return False
    if submission.is_self:
        return False
    if submission.is_video:
        return False
    if not submission.url:
        return False
    return True


def download_image(url: str, filename: str) -> Path | None:
    dest = IMAGES_DIR / filename
    if dest.exists():
        return dest
    try:
        resp = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": config.REDDIT_USER_AGENT},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type and "octet-stream" not in content_type:
            return None
        dest.write_bytes(resp.content)
        return dest
    except Exception:
        return None


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", text)[:max_len].strip("_")
    return s or "untitled"


def crawl() -> None:
    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
    )

    existing = load_manifest()
    seen_ids = {e["id"] for e in existing}
    entries = list(existing)
    new_count = 0

    subreddit = reddit.subreddit(config.SUBREDDIT)

    try:
        for submission in subreddit.top(time_filter=config.TIME_FILTER, limit=config.LIMIT):
            if submission.id in seen_ids:
                continue

            if not is_valid_submission(submission):
                continue

            image_url = resolve_image_url(submission)
            if not image_url:
                continue

            ext = safe_ext(image_url) or ".jpg"
            filename = f"{submission.id}_{slugify(submission.title)}{ext}"

            local_path = download_image(image_url, filename)
            if not local_path:
                continue

            entry = {
                "id": submission.id,
                "post_title": submission.title,
                "image_url": image_url,
                "image_path": str(local_path),
                "permalink": f"https://reddit.com{submission.permalink}",
                "upvotes": submission.score,
                "source_subreddit": config.SUBREDDIT,
                "meme_template_name": (submission.link_flair_text or "").strip() or None,
                "created_utc": submission.created_utc,
            }

            entries.append(entry)
            seen_ids.add(submission.id)
            new_count += 1

            if new_count % CHECKPOINT_INTERVAL == 0:
                save_manifest(entries)
                print(f"Checkpoint: {len(entries)} total, {new_count} new")

            time.sleep(0.3)
    finally:
        save_manifest(entries)
        print(f"Saved: {len(entries)} total, {new_count} new")


if __name__ == "__main__":
    crawl()
