from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

RETRY_DELAYS = [5, 15, 30, 60]


async def _with_retry(coro_fn):
    for attempt, delay in enumerate(RETRY_DELAYS + [None]):
        try:
            return await coro_fn()
        except Exception as e:
            if "429" not in str(e) or delay is None:
                raise
            await asyncio.sleep(delay)

from backend import config
from backend.clients import (
    close_all,
    ensure_collection,
    mistral_embed,
    mistral_vision_describe,
    neo4j_upsert_caption,
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

        if entry.get("use_vlm"):
            try:
                vlm_desc = await _with_retry(lambda: mistral_vision_describe(image_path))
            except Exception:
                vlm_desc = ""
            if vlm_desc:
                ocr_text = f"[visual]: {vlm_desc}\n[ocr]: {ocr_text or '(no text)'}"

        try:
            decoded, template_from_llm = await _with_retry(
                lambda: decode_meme(
                    title=entry["post_title"],
                    ocr_text=ocr_text,
                    subreddit=entry.get("source_subreddit", config.SUBREDDIT),
                )
            )
        except DecodeError as e:
            quarantine.append({"id": reddit_id, "reason": f"decode: {e}"})
            return False
        except Exception as e:
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
            irony_vec = await _with_retry(lambda: mistral_embed(decoded.search_dense_explanations))
        except Exception as e:
            quarantine.append({"id": reddit_id, "reason": f"mistral_embed: {e}"})
            return False

        point_id = str(uuid5(NAMESPACE_URL, reddit_id))

        payload = {
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
            "indexed_at": int(time.time()),
        }
        if entry.get("image_sha256"):
            payload["image_sha256"] = entry["image_sha256"]

        await qdrant_upsert_point(
            point_id=point_id,
            visual_vec=visual_vec,
            irony_vec=irony_vec,
            payload=payload,
        )

        try:
            await neo4j_upsert_meme(
                meme_id=reddit_id,
                template=template,
                title=entry["post_title"],
                upvotes=entry["upvotes"],
                permalink=entry["permalink"],
                core_joke=decoded.core_joke,
                image_path=entry["image_path"],
            )
            await neo4j_upsert_caption(
                meme_id=reddit_id,
                lang="en",
                core_joke=decoded.core_joke,
                psychological_state=decoded.psychological_state,
                subtext_context=decoded.subtext_context,
                search_dense_explanations=decoded.search_dense_explanations,
            )
        except Exception as e:
            quarantine.append({"id": reddit_id, "reason": f"neo4j_best_effort: {e}", "qdrant_ok": True})

        return True


async def ingest_upload(
    image_path: Path,
    image_sha256: str,
    title: str | None,
    image_url: str | None = None,
) -> tuple[str, bool]:
    reddit_id = f"upload:{image_sha256}"
    _image_url = image_url or f"/static/images/{image_path.name}"
    entry = {
        "id": reddit_id,
        "image_path": str(image_path),
        "post_title": (title or "user upload").strip() or "user upload",
        "image_url": _image_url,
        "permalink": _image_url,
        "upvotes": 0,
        "source_subreddit": "uploads",
        "meme_template_name": None,
        "image_sha256": image_sha256,
        "use_vlm": True,
    }
    semaphore = asyncio.Semaphore(1)
    quarantine: list[dict] = []
    ok = await ingest_one(entry, semaphore, quarantine)
    point_id = str(uuid5(NAMESPACE_URL, reddit_id))
    return point_id, ok


async def run(workers: int, limit: int | None, delay: float, manifest: str | None = None) -> None:
    manifest_path = Path(manifest) if manifest else config.DATA_DIR / "memes.json"
    if not manifest_path.exists():
        print(f"No manifest found at {manifest_path}")
        sys.exit(1)

    entries = json.loads(manifest_path.read_text())
    if limit:
        entries = entries[:limit]

    total = len(entries)
    print(f"Starting ingest: {total} memes, {workers} workers, {delay}s launch stagger")
    await ensure_collection()

    semaphore = asyncio.Semaphore(workers)
    quarantine: list[dict] = []
    progress = {"done": 0, "ok": 0}

    async def _worker(entry: dict) -> bool:
        result = await ingest_one(entry, semaphore, quarantine)
        progress["done"] += 1
        if result is True:
            progress["ok"] += 1
        print(f"[{progress['done']}/{total}] {entry['id']} -> {'ok' if result else 'quarantined'}")
        return result

    tasks = []
    for entry in entries:
        tasks.append(asyncio.create_task(_worker(entry)))
        if delay > 0:
            await asyncio.sleep(delay)
    await asyncio.gather(*tasks)

    ok = progress["ok"]

    if quarantine:
        quarantine_path = config.DATA_DIR / "quarantine.json"
        quarantine_path.write_text(json.dumps(quarantine, indent=2))
        print(f"Quarantined {len(quarantine)} memes -> {quarantine_path}")

    print(f"Ingest complete: {ok} ok, {len(quarantine)} quarantined")

    await close_all()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--manifest", type=str, default=None)
    args = parser.parse_args()
    asyncio.run(run(args.workers, args.limit, args.delay, args.manifest))


if __name__ == "__main__":
    main()
