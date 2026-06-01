"""Merge scraped KYM JSON (from bookmarklet) into existing data/knowyourmeme_latest/.

Usage: uv run python scripts/merge_kym_scrape.py <scraped_file.json>
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


def slugify(text: str, max_len: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return (slug or "entry")[:max_len].strip("-")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scraped_file", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("data/knowyourmeme_latest"))
    args = parser.parse_args()

    out_dir = args.out_dir
    index_path = out_dir / "index.json"
    info_dir = out_dir / "information"
    info_dir.mkdir(parents=True, exist_ok=True)

    # Load existing
    existing = []
    seen_urls = set()
    if index_path.exists():
        existing = json.loads(index_path.read_text(encoding="utf-8"))
        seen_urls = {rec["url"] for rec in existing if "url" in rec}
    print(f"Existing entries: {len(existing)}")

    # Load scraped
    scraped = json.loads(args.scraped_file.read_text(encoding="utf-8"))
    print(f"Scraped entries: {len(scraped)}")

    # Merge: skip duplicates by URL
    added = 0
    for item in scraped:
        url = item.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        idx = len(existing) + 1
        slug = f"{idx:03d}-{slugify(item.get('title', 'unknown'))}"

        record = {
            "id": slug,
            "rank": idx,
            "title": item.get("title", ""),
            "url": url,
            "listing_page": item.get("listing_page", 0),
            "status": item.get("status"),
            "type": item.get("type"),
            "year": item.get("year"),
            "origin_label": item.get("origin_label"),
            "about": item.get("about"),
            "origin": item.get("origin"),
            "image_url": item.get("image_url"),
            "image_path": None,  # Images not downloaded by bookmarklet
        }

        (info_dir / f"{slug}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        existing.append(record)
        added += 1
        print(f"  [{idx:03d}] {record['title']}")

    # Save updated index
    index_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nDone. {added} new entries added. Total: {len(existing)}")


if __name__ == "__main__":
    main()
