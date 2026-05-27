from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from backend import config
from backend.clients import (
    close_all,
    ensure_collection,
    mistral_embed,
    neo4j_upsert_meme,
    qdrant_upsert_point,
    tl_embed_image_file,
)
from backend.decoder import DecodeError, decode_meme, extract_text


def _normalize_template(raw: str | None, title: str) -> str:
    if raw:
        return raw.strip().lower().replace(" ", "_")[:64]
    words = [w for w in title.lower().split() if w.isalpha()][:3]
    return ("_".join(words) or "uncategorized")[:64]


async def ingest_one(
    entry: dict,
    semaphore: asyncio.Semaphore,
    quarantine: list[dict],
) -> bool:
    async with semaphore:
        reddit_id = entry["id"]
        image_path = Path(entry["image_path"])

        if not image_path.exists():
            quarantine.append({"id": reddit_id, "reason": "image_missing"})
            return False

        ocr_text = await extract_text(image_path)

        try:
            decoded, template_from_llm = await decode_meme(
                title=entry["post_title"],
                ocr_text=ocr_text,
                subreddit=entry.get("source_subreddit", config.SUBREDDIT),
            )
        except DecodeError as e:
            quarantine.append({"id": reddit_id, "reason": f"decode: {e}"})
            return False

        template = _normalize_template(
            template_from_llm if template_from_llm != "unknown" else entry.get("meme_template_name"),
            entry["post_title"],
        )

        try:
            visual_vec = await tl_embed_image_file(image_path)
        except Exception as e:
            quarantine.append({"id": reddit_id, "reason": f"tl_embed: {e}"})
            return False

        try:
            irony_vec = await mistral_embed(decoded.search_dense_explanations)
        except Exception as e:
            quarantine.append({"id": reddit_id, "reason": f"mistral_embed: {e}"})
            return False

        point_id = str(uuid5(NAMESPACE_URL, reddit_id))

        await qdrant_upsert_point(
            point_id=point_id,
            visual_vec=visual_vec,
            irony_vec=irony_vec,
            payload={
                "reddit_id": reddit_id,
                "title": entry["post_title"],
                "ocr_text": ocr_text,
                "image_url": entry["image_url"],
                "permalink": entry["permalink"],
                "upvotes": entry["upvotes"],
                "source_subreddit": entry.get("source_subreddit", config.SUBREDDIT),
                "template": template,
                "core_joke": decoded.core_joke,
                "psychological_state": decoded.psychological_state,
                "subtext_context": decoded.subtext_context,
                "search_dense_explanations": decoded.search_dense_explanations,
            },
        )

        await neo4j_upsert_meme(
            meme_id=reddit_id,
            template=template,
            title=entry["post_title"],
            upvotes=entry["upvotes"],
            permalink=entry["permalink"],
            core_joke=decoded.core_joke,
            image_path=entry["image_path"],
        )

        return True


async def run(workers: int, limit: int | None) -> None:
    manifest_path = config.DATA_DIR / "memes.json"
    if not manifest_path.exists():
        print(f"No manifest found at {manifest_path}")
        sys.exit(1)

    entries = json.loads(manifest_path.read_text())
    if limit:
        entries = entries[:limit]

    print(f"Starting ingest: {len(entries)} memes, {workers} workers")
    await ensure_collection()

    semaphore = asyncio.Semaphore(workers)
    quarantine: list[dict] = []

    tasks = [ingest_one(entry, semaphore, quarantine) for entry in entries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    ok = sum(1 for r in results if r is True)
    errors = sum(1 for r in results if isinstance(r, Exception))

    for i, r in enumerate(results):
        if isinstance(r, Exception):
            quarantine.append({"id": entries[i]["id"], "reason": str(r)})

    if quarantine:
        quarantine_path = config.DATA_DIR / "quarantine.json"
        quarantine_path.write_text(json.dumps(quarantine, indent=2))
        print(f"Quarantined {len(quarantine)} memes -> {quarantine_path}")

    print(f"Ingest complete: {ok} ok, {len(quarantine)} quarantined, {errors} exceptions")

    await close_all()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(run(args.workers, args.limit))


if __name__ == "__main__":
    main()
