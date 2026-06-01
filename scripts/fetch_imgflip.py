from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import config

GITHUB_RAW = "https://raw.githubusercontent.com/schesa/ImgFlip575K_Dataset/master/dataset/memes"

TEMPLATES = {
    "Expanding-Brain": "expanding_brain",
}

SAMPLES_PER_TEMPLATE = 8
OUTPUT_FILE = config.DATA_DIR / "imgflip_memes.json"
IMAGES_DIR = config.DATA_DIR / "images"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "memeradar-fetch/0.1"})


def fetch_template_memes(template_file: str) -> list[dict]:
    url = f"{GITHUB_RAW}/{template_file}.json"
    resp = SESSION.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    for key in ("memes", "data", "items", "results"):
        if key in data and isinstance(data[key], list):
            return data[key]
    return []


def _img_url(meme: dict) -> str:
    for key in ("img", "image_url", "url", "image"):
        val = meme.get(key, "")
        if val and ("imgflip.com" in val or val.startswith("http")):
            if key != "url" or val.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                return val
    return ""


def _permalink(meme: dict, img_url: str) -> str:
    if meme.get("page_url"):
        return meme["page_url"]
    if meme.get("url") and not meme["url"].endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return meme["url"]
    stem = Path(img_url.split("?")[0]).stem
    return f"https://imgflip.com/i/{stem}"


def _title(meme: dict, template_file: str, index: int) -> str:
    if meme.get("title"):
        return meme["title"][:200]
    boxes = meme.get("boxes") or meme.get("box_count") or []
    if isinstance(boxes, list):
        texts = [b["text"] if isinstance(b, dict) else str(b) for b in boxes if b]
        caption = " | ".join(t for t in texts if t)
        if caption:
            return caption[:200]
    name = template_file.replace("-", " ")
    return f"{name} #{index + 1}"


def download_image(url: str, path: Path) -> bool:
    try:
        resp = SESSION.get(url, timeout=15, stream=True)
        resp.raise_for_status()
        content = resp.content
        if len(content) < 500:
            return False
        path.write_bytes(content)
        return True
    except Exception as exc:
        print(f"    download failed: {exc}")
        return False


def main() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []

    for template_file, template_slug in TEMPLATES.items():
        print(f"\nFetching {template_file}...")
        try:
            all_memes = fetch_template_memes(template_file)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            continue

        print(f"  Found {len(all_memes)} memes total, sampling {SAMPLES_PER_TEMPLATE}")

        sampled = 0
        for raw in all_memes:
            if sampled >= SAMPLES_PER_TEMPLATE:
                break

            img_url = _img_url(raw)
            if not img_url:
                continue

            idx = sampled
            meme_id = f"imgflip-{template_slug}-{idx + 1:03d}"
            ext = Path(img_url.split("?")[0]).suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                ext = ".jpg"
            img_filename = f"{meme_id}{ext}"
            img_path = IMAGES_DIR / img_filename

            print(f"  [{idx + 1}/{SAMPLES_PER_TEMPLATE}] {meme_id} <- {img_url}")
            if not download_image(img_url, img_path):
                print(f"    skipped (bad download)")
                continue

            entries.append({
                "id": meme_id,
                "image_path": str(img_path),
                "post_title": _title(raw, template_file, idx),
                "image_url": img_url,
                "permalink": _permalink(raw, img_url),
                "upvotes": int(raw.get("votes", raw.get("upvotes", 0)) or 0),
                "source_subreddit": "imgflip",
                "meme_template_name": template_slug,
            })
            sampled += 1
            time.sleep(0.15)

        print(f"  Saved {sampled} entries for {template_slug}")

    existing: list[dict] = []
    if OUTPUT_FILE.exists():
        existing = json.loads(OUTPUT_FILE.read_text())
    existing_ids = {e["id"] for e in existing}
    new_entries = [e for e in entries if e["id"] not in existing_ids]
    OUTPUT_FILE.write_text(json.dumps(existing + new_entries, indent=2))
    print(f"\nDone. {len(entries)} entries -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
