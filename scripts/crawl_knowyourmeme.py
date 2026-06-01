from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://knowyourmeme.com"
LIST_URL = f"{BASE_URL}/memes"
USER_AGENT = "MemeFinder/0.1 (+https://knowyourmeme.com; educational local scrape)"
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


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def section_text(soup: BeautifulSoup, section_name: str) -> str | None:
    heading = soup.find(
        lambda tag: tag.name in {"h2", "h3"}
        and clean_text(tag.get_text(" ", strip=True)).lower() == section_name.lower()
    )
    if not heading:
        return None

    chunks: list[str] = []
    for sibling in heading.next_siblings:
        if getattr(sibling, "name", None) in {"h1", "h2"}:
            break
        if getattr(sibling, "name", None) in {"p", "blockquote", "ul", "ol"}:
            text = clean_text(sibling.get_text(" ", strip=True))
            if text:
                chunks.append(text)

    return "\n\n".join(chunks) or None


def meta_value(soup: BeautifulSoup, label: str) -> str | None:
    for dt in soup.find_all("dt"):
        if clean_text(dt.get_text(" ", strip=True)).rstrip(":").lower() == label.lower():
            dd = dt.find_next_sibling("dd")
            if dd:
                return clean_text(dd.get_text(" ", strip=True))
    return None


def image_url_from_page(soup: BeautifulSoup) -> str | None:
    for selector, attr in (
        ('meta[property="og:image"]', "content"),
        ('meta[name="twitter:image"]', "content"),
        ("img.thumbnail", "src-large"),
        ("img.thumbnail", "src"),
    ):
        tag = soup.select_one(selector)
        if tag and tag.get(attr):
            return urljoin(BASE_URL, tag[attr])
    return None


def title_from_page(soup: BeautifulSoup, fallback: str) -> str:
    title = soup.select_one("h1.entry-title") or soup.select_one("h1.content-title")
    if title:
        return clean_text(title.get_text(" ", strip=True))
    if soup.title:
        return clean_text(soup.title.get_text(" ", strip=True).replace("| Know Your Meme", ""))
    return fallback


def meta_description(soup: BeautifulSoup) -> str | None:
    for selector in ('meta[name="description"]', 'meta[property="og:description"]'):
        tag = soup.select_one(selector)
        if tag and tag.get("content"):
            return clean_text(tag["content"])
    return None


def fetch(session: requests.Session, url: str, sleep: float, retries: int = 3) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            if sleep:
                time.sleep(sleep)
            return response
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(min(5, attempt * 1.5))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def listing_entries(session: requests.Session, page: int, sleep: float) -> list[dict[str, str]]:
    url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
    soup = BeautifulSoup(fetch(session, url, sleep).text, "html.parser")
    entries: list[dict[str, str]] = []

    for link in soup.select('a.item[href^="/memes/"]'):
        href = link.get("href")
        if not href:
            continue
        raw_title = clean_text(link.get_text(" ", strip=True)).split("★", 1)[0].strip()
        entries.append(
            {
                "title": raw_title,
                "url": urljoin(BASE_URL, href),
                "listing_page": str(page),
            }
        )

    return entries


def choose_image_extension(response: requests.Response, url: str) -> str:
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type in IMAGE_EXTENSIONS:
        return IMAGE_EXTENSIONS[content_type]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def download_image(session: requests.Session, url: str, dest_without_ext: Path) -> Path | None:
    try:
        response = fetch(session, url, sleep=0)
    except RuntimeError as exc:
        print(f"image failed: {url} ({exc})")
        return None

    if not response.headers.get("content-type", "").lower().startswith("image/"):
        print(f"image skipped: {url} returned {response.headers.get('content-type')}")
        return None

    dest = dest_without_ext.with_suffix(choose_image_extension(response, url))
    dest.write_bytes(response.content)
    return dest


def scrape_entry(
    session: requests.Session,
    entry: dict[str, str],
    index: int,
    picture_dir: Path,
    information_dir: Path,
    sleep: float,
) -> dict[str, str | int | None]:
    response = fetch(session, entry["url"], sleep)
    soup = BeautifulSoup(response.text, "html.parser")
    title = title_from_page(soup, entry["title"])
    slug = f"{index:03d}-{slugify(title)}"

    about = section_text(soup, "About") or section_text(soup, "Overview") or meta_description(soup)
    origin = section_text(soup, "Origin") or meta_value(soup, "Origin")
    image_url = image_url_from_page(soup)
    image_path = None

    if image_url:
        downloaded = download_image(session, image_url, picture_dir / slug)
        image_path = str(downloaded.resolve()) if downloaded else None

    record: dict[str, str | int | None] = {
        "id": slug,
        "rank": index,
        "title": title,
        "url": entry["url"],
        "listing_page": int(entry["listing_page"]),
        "status": meta_value(soup, "Status"),
        "type": meta_value(soup, "Type"),
        "year": meta_value(soup, "Year"),
        "origin_label": meta_value(soup, "Origin"),
        "about": about,
        "origin": origin,
        "image_url": image_url,
        "image_path": image_path,
    }

    (information_dir / f"{slug}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record


def scrape(limit: int, out_dir: Path, sleep: float, max_pages: int) -> list[dict[str, str | int | None]]:
    picture_dir = out_dir / "picture"
    information_dir = out_dir / "information"
    picture_dir.mkdir(parents=True, exist_ok=True)
    information_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})

    records: list[dict[str, str | int | None]] = []
    seen_urls: set[str] = set()

    index_path = out_dir / "index.json"
    if index_path.exists():
        existing = json.loads(index_path.read_text(encoding="utf-8"))
        for rec in existing:
            url = rec.get("url")
            if url:
                seen_urls.add(url)
        records = existing
        print(f"loaded {len(records)} existing entries; will skip duplicates")

    for page in range(1, max_pages + 1):
        entries = listing_entries(session, page, sleep)
        if not entries:
            break

        for entry in entries:
            if entry["url"] in seen_urls:
                continue
            seen_urls.add(entry["url"])

            try:
                record = scrape_entry(
                    session=session,
                    entry=entry,
                    index=len(records) + 1,
                    picture_dir=picture_dir,
                    information_dir=information_dir,
                    sleep=sleep,
                )
            except Exception as exc:
                print(f"entry failed: {entry['url']} ({exc})")
                continue

            records.append(record)
            print(f"[{len(records):03d}/{limit}] {record['title']}")

            if len(records) >= limit:
                (out_dir / "index.json").write_text(
                    json.dumps(records, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return records

    (out_dir / "index.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out-dir", type=Path, default=Path("data/knowyourmeme_latest"))
    parser.add_argument("--sleep", type=float, default=0.35)
    parser.add_argument("--max-pages", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = scrape(args.limit, args.out_dir, args.sleep, args.max_pages)
    print(f"done. saved {len(records)} entries to {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()
