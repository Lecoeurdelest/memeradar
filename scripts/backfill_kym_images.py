"""Download missing images for KYM entries and update image_path in index.json.

Usage: uv run python scripts/backfill_kym_images.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

INDEX_PATH = Path("data/knowyourmeme_latest/index.json")
PICTURE_DIR = Path("data/knowyourmeme_latest/picture")
IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SLEEP = 0.3


def main():
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    PICTURE_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    missing = [d for d in index if d.get("image_url") and not d.get("image_path")]
    print(f"Entries missing images: {len(missing)} / {len(index)}")

    downloaded = 0
    skipped = 0
    failed = 0

    for entry in missing:
        url = entry["image_url"]
        entry_id = entry.get("id", "unknown")

        # Determine extension from URL first as fallback
        url_suffix = Path(url.split("?")[0]).suffix.lower()
        fallback_ext = url_suffix if url_suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else ".jpg"
        if fallback_ext == ".jpeg":
            fallback_ext = ".jpg"

        # Check if file already exists with any extension
        existing = list(PICTURE_DIR.glob(f"{entry_id}.*"))
        if existing:
            entry["image_path"] = str(existing[0].resolve())
            skipped += 1
            continue

        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()

            ct = resp.headers.get("content-type", "").split(";")[0].lower()
            ext = IMAGE_EXTENSIONS.get(ct, fallback_ext)

            dest = PICTURE_DIR / f"{entry_id}{ext}"
            dest.write_bytes(resp.content)
            entry["image_path"] = str(dest.resolve())

            downloaded += 1
            print(f"  [{downloaded}/{len(missing)}] {entry_id}{ext} ({len(resp.content)} bytes)")

        except Exception as exc:
            failed += 1
            print(f"  FAILED: {entry_id} - {exc}")

        time.sleep(SLEEP)

    # Save updated index
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")
    print(f"Total entries: {len(index)}")


if __name__ == "__main__":
    main()
