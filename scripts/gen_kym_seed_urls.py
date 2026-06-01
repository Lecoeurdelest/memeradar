"""Generate a JS snippet of existing KYM URLs for the bookmarklet to skip.

Usage: uv run python scripts/gen_kym_seed_urls.py
Paste the output into Chrome console BEFORE running kym_scraper_bookmarklet.js
"""
from __future__ import annotations

import json
from pathlib import Path

INDEX_PATH = Path("data/knowyourmeme_latest/index.json")


def main():
    if not INDEX_PATH.exists():
        print("// No existing index.json — nothing to skip")
        return

    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    urls = [d["url"] for d in data if "url" in d]

    # The bookmarklet checks: if (SEEN.has(entry.url) || EXISTING_URLS.has(entry.url)) continue;
    # So we just need to define EXISTING_URLS as a Set.
    lines = ["const EXISTING_URLS = new Set(["]
    for i, url in enumerate(urls):
        comma = "," if i < len(urls) - 1 else ""
        lines.append(f'  {json.dumps(url)}{comma}')
    lines.append("]);")

    snippet = "\n".join(lines)
    print(snippet)
    print(f"\n// {len(urls)} URLs loaded. Paste the block above, then paste the bookmarklet.")
    print("// Make sure the bookmarklet has this line (it already does in the latest version):")
    print("//   if (SEEN.has(entry.url) || (typeof EXISTING_URLS !== 'undefined' && EXISTING_URLS.has(entry.url))) continue;")


if __name__ == "__main__":
    main()
