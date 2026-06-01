"""Interactive KYM scraper — opens a visible browser for manual CF challenge, then auto-scrapes.

Usage: uv run python scripts/crawl_knowyourmeme_playwright.py --limit 200
"""
from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

BASE_URL = "https://knowyourmeme.com"
LIST_URL = f"{BASE_URL}/memes"
IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def slugify(text: str, max_len: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return (slug or "entry")[:max_len].strip("-")


def load_existing(index_path: Path) -> tuple[list[dict], set[str]]:
    if not index_path.exists():
        return [], set()
    existing = json.loads(index_path.read_text(encoding="utf-8"))
    seen = {rec["url"] for rec in existing if "url" in rec}
    print(f"Loaded {len(existing)} existing entries; {len(seen)} URLs seen")
    return existing, seen


def scrape_listing_page(page, page_num: int) -> list[dict[str, str]]:
    """Extract all meme entry links from a listing page."""
    url = LIST_URL if page_num == 1 else f"{LIST_URL}?page={page_num}"
    print(f"  Fetching listing page {page_num}...")
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Wait for meme entry links to appear
    try:
        page.wait_for_selector('a[href*="/memes/"]', timeout=10000)
    except Exception:
        pass

    entries = page.evaluate("""
        (pageNum) => {
            const results = [];
            const seen = new Set();
            const links = document.querySelectorAll('a[href*="/memes/"]');
            for (const a of links) {
                const href = a.getAttribute('href');
                const title = (a.textContent || '').trim();
                if (href && title && title.length > 3 &&
                    /^\\/memes\\/[^\\/\\?]+(\\/)?$/.test(href) &&
                    !href.includes('/subcultures/') &&
                    !href.includes('/events/') &&
                    !href.includes('/people/') &&
                    !href.includes('/sites/')) {
                    const fullUrl = 'https://knowyourmeme.com' + href.replace(/\\/$/, '');
                    if (!seen.has(fullUrl)) {
                        seen.add(fullUrl);
                        results.push({ url: fullUrl, title: title, listing_page: String(pageNum) });
                    }
                }
            }
            return results;
        }
    """, page_num)
    print(f"  Found {len(entries)} entries on page {page_num}")
    return entries


def scrape_detail(page, entry: dict, index: int, picture_dir: Path, info_dir: Path, sleep: float) -> dict | None:
    """Scrape a single meme detail page."""
    try:
        page.goto(entry["url"], timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(sleep * 1000)

        data = page.evaluate("""
            () => {
                const getMeta = (label) => {
                    const dts = document.querySelectorAll('dt');
                    for (const dt of dts) {
                        if (dt.textContent.trim().toLowerCase().startsWith(label.toLowerCase())) {
                            const dd = dt.nextElementSibling;
                            return dd ? dd.textContent.trim() : null;
                        }
                    }
                    return null;
                };
                const getSection = (name) => {
                    const headings = document.querySelectorAll('h2, h3');
                    for (const h of headings) {
                        if (h.textContent.trim().toLowerCase() === name.toLowerCase()) {
                            const parts = [];
                            let next = h.nextElementSibling;
                            while (next && !['H1','H2'].includes(next.tagName)) {
                                if (['P','BLOCKQUOTE','UL','OL'].includes(next.tagName)) {
                                    const t = next.textContent.trim();
                                    if (t) parts.push(t);
                                }
                                next = next.nextElementSibling;
                            }
                            return parts.join('\\n\\n') || null;
                        }
                    }
                    return null;
                };
                const getMetaDesc = () => {
                    const meta = document.querySelector('meta[name="description"], meta[property="og:description"]');
                    return meta ? meta.getAttribute('content') : null;
                };
                const getOgImage = () => {
                    const meta = document.querySelector('meta[property="og:image"]');
                    return meta ? meta.getAttribute('content') : null;
                };
                const titleEl = document.querySelector('h1.entry-title') || document.querySelector('h1');
                return {
                    title: titleEl ? titleEl.textContent.trim() : '',
                    status: getMeta('Status'),
                    type: getMeta('Type'),
                    year: getMeta('Year'),
                    origin_label: getMeta('Origin'),
                    about: getSection('About') || getSection('Overview') || getMetaDesc(),
                    origin: getSection('Origin') || getMeta('Origin'),
                    image_url: getOgImage(),
                };
            }
        """)
    except Exception as exc:
        print(f"  FAILED: {entry['url']} ({exc})")
        return None

    slug = f"{index:03d}-{slugify(data['title'] or entry['title'])}"
    image_path = None

    # Download image
    if data.get("image_url"):
        try:
            img_response = page.request.get(data["image_url"], timeout=15000)
            if img_response.ok and img_response.headers.get("content-type", "").startswith("image/"):
                ct = img_response.headers["content-type"].split(";")[0].lower()
                ext = IMAGE_EXTENSIONS.get(ct, ".jpg")
                dest = picture_dir / f"{slug}{ext}"
                dest.write_bytes(img_response.body())
                image_path = str(dest.resolve())
        except Exception as exc:
            print(f"  Image download failed: {exc}")

    record = {
        "id": slug,
        "rank": index,
        "title": data["title"] or entry["title"],
        "url": entry["url"],
        "listing_page": int(entry.get("listing_page", 0)),
        "status": data.get("status"),
        "type": data.get("type"),
        "year": data.get("year"),
        "origin_label": data.get("origin_label"),
        "about": data.get("about"),
        "origin": data.get("origin"),
        "image_url": data.get("image_url"),
        "image_path": image_path,
    }

    (info_dir / f"{slug}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--out-dir", type=Path, default=Path("data/knowyourmeme_latest"))
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--max-pages", type=int, default=10)
    args = parser.parse_args()

    picture_dir = args.out_dir / "picture"
    info_dir = args.out_dir / "information"
    picture_dir.mkdir(parents=True, exist_ok=True)
    info_dir.mkdir(parents=True, exist_ok=True)

    index_path = args.out_dir / "index.json"
    records, seen_urls = load_existing(index_path)

    if len(records) >= args.limit:
        print(f"Already have {len(records)} entries (limit={args.limit}). Nothing to do.")
        return

    print(f"Need {args.limit - len(records)} more entries.")
    print("\n*** Opening browser window — please solve the Cloudflare challenge if one appears ***")
    print("*** The script will wait 30s for you, then start scraping ***\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to listing page so user can solve CF
        page.goto(LIST_URL, timeout=30000, wait_until="domcontentloaded")
        print("Browser opened. If you see 'Just a moment...', please wait for it to pass.")
        print("Waiting 15 seconds for CF challenge...")
        page.wait_for_timeout(15000)
        print("Starting scrape...\n")

        for page_num in range(1, args.max_pages + 1):
            if len(records) >= args.limit:
                break

            entries = scrape_listing_page(page, page_num)
            if not entries:
                print(f"No entries on page {page_num}, stopping.")
                break

            for entry in entries:
                if len(records) >= args.limit:
                    break
                if entry["url"] in seen_urls:
                    continue
                seen_urls.add(entry["url"])

                record = scrape_detail(
                    page, entry, len(records) + 1,
                    picture_dir, info_dir, args.sleep
                )
                if record:
                    records.append(record)
                    print(f"  [{len(records):03d}/{args.limit}] {record['title']}")

            # Save checkpoint after each page
            index_path.write_text(
                json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"  (checkpoint saved: {len(records)} entries)\n")

        browser.close()

    print(f"\nDone. {len(records)} entries saved to {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()
