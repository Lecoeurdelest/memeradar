from __future__ import annotations

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from qdrant_client.models import PointStruct

from . import clients as c
from . import config as cfg


def _public_url(image_path: str) -> str:
    name = Path(image_path).name
    return f"{cfg.PUBLIC_IMAGE_BASE}/{name}"


def _normalize_template(raw: str | None, title: str) -> str:
    if raw:
        return raw.strip().lower().replace(" ", "_")[:64]
    words = [w for w in title.lower().split() if w.isalpha()][:3]
    return ("_".join(words) or "uncategorized")[:64]


def process_one(meme: dict) -> dict | None:
    try:
        image_url = _public_url(meme["image_path"])
        ocr_text = c.ocr_image(meme["image_path"])
        irony = c.mistral_irony(meme["post_title"], ocr_text)

        visual_vec = c.tl_image_embedding(image_url)
        irony_vec = c.mistral_embed(irony)

        template = _normalize_template(meme.get("meme_template_name"), meme["post_title"])

        c.neo4j_upsert_meme(
            meme_id=meme["id"],
            template=template,
            title=meme["post_title"],
            upvotes=meme["upvotes"],
            permalink=meme["permalink"],
            irony=irony,
            image_path=meme["image_path"],
        )

        point = PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, meme["id"])),
            vector={"visual": visual_vec, "irony": irony_vec},
            payload={
                "reddit_id": meme["id"],
                "title": meme["post_title"],
                "ocr_text": ocr_text,
                "irony": irony,
                "template": template,
                "upvotes": meme["upvotes"],
                "permalink": meme["permalink"],
                "image_url": image_url,
            },
        )
        c.qdrant.upsert(collection_name=cfg.COLLECTION, points=[point])
        return {"id": meme["id"], "ok": True}
    except Exception as e:
        return {"id": meme["id"], "ok": False, "error": str(e)}


def run(meta_file: Path = cfg.META_FILE, workers: int = 4, limit: int | None = None):
    c.ensure_collection()
    memes = json.loads(meta_file.read_text())
    if limit:
        memes = memes[:limit]

    ok = fail = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(process_one, m) for m in memes]
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            ok += int(r["ok"])
            fail += int(not r["ok"])
            if not r["ok"]:
                print(f"  fail {r['id']}: {r['error']}")
            if i % 25 == 0:
                print(f"[{i}/{len(memes)}] ok={ok} fail={fail} elapsed={time.time()-t0:.0f}s")

    print(f"done. ok={ok} fail={fail}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    run(workers=args.workers, limit=args.limit)
