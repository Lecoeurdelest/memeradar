from __future__ import annotations

import asyncio
import mimetypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config
from backend.clients import get_qdrant
from backend.storage import s3_exists, s3_public_url, s3_upload

_PICTURE_DIRS = [
    config.DATA_DIR / "knowyourmeme_latest" / "picture",
    config.DATA_DIR / "knowyourmeme_latest_test" / "picture",
    config.DATA_DIR / "images",
]

_STEM_TO_PATH: dict[str, Path] = {}
for _d in _PICTURE_DIRS:
    if _d.exists():
        for _f in _d.iterdir():
            if _f.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                _STEM_TO_PATH[_f.stem] = _f


def _s3_key(filename: str) -> str:
    return f"memes/{filename}"


async def _upload_one(path: Path) -> str:
    key = _s3_key(path.name)
    if not await s3_exists(key):
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        data = path.read_bytes()
        await s3_upload(key, data, mime)
    return s3_public_url(key)


async def main() -> None:
    if not config.S3_ENABLED:
        print("S3 not configured — aborting")
        sys.exit(1)

    qdrant = get_qdrant()
    offset = None
    total = updated = skipped = missing = 0

    while True:
        results, next_offset = await qdrant.scroll(
            config.QDRANT_COLLECTION,
            offset=offset,
            limit=50,
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            break

        for point in results:
            total += 1
            pid = str(point.id)
            payload = point.payload or {}
            current_url: str = payload.get("image_url", "")

            if "amazonaws.com" in current_url:
                skipped += 1
                print(f"[skip]    {pid} already S3")
                continue

            meme_id: str = payload.get("reddit_id", "") or payload.get("id", "")
            stem = meme_id.split(":")[0] if meme_id else ""

            local_path = _STEM_TO_PATH.get(stem)
            if local_path is None:
                for candidate_stem, candidate_path in _STEM_TO_PATH.items():
                    if candidate_stem.startswith(stem[:6]) and stem:
                        local_path = candidate_path
                        break

            if local_path is None:
                missing += 1
                print(f"[missing] {pid} ({stem}) — no local file")
                continue

            try:
                new_url = await _upload_one(local_path)
            except Exception as exc:
                print(f"[error]   {pid} upload failed: {exc}")
                continue

            await qdrant.set_payload(
                config.QDRANT_COLLECTION,
                payload={"image_url": new_url},
                points=[point.id],
            )
            updated += 1
            print(f"[ok]      {pid} → {new_url}")

        if next_offset is None:
            break
        offset = next_offset

    print(f"\nDone: {total} total, {updated} updated, {skipped} already S3, {missing} missing local file")


if __name__ == "__main__":
    asyncio.run(main())
