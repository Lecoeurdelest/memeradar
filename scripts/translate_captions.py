from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.clients import close_all, get_neo4j_driver, neo4j_upsert_caption, scroll_all_payloads
from backend.translate import SUPPORTED_LANGUAGES, translate_caption

RETRY_DELAYS = [5, 15, 30, 60]


async def _with_retry(coro_fn):
    for attempt, delay in enumerate(RETRY_DELAYS + [None]):
        try:
            return await coro_fn()
        except Exception as e:
            if "429" not in str(e) or delay is None:
                raise
            await asyncio.sleep(delay)


async def already_translated(meme_id: str, lang: str) -> bool:
    driver = get_neo4j_driver()
    query = (
        "MATCH (m:Meme {id: $meme_id})-[:HAS_CAPTION]->(c:MemeCaption {lang: $lang}) "
        "RETURN count(c) AS n"
    )
    async with driver.session() as session:
        result = await session.run(query, meme_id=meme_id, lang=lang)
        record = await result.single()
        return record and record["n"] > 0


async def translate_one(payload: dict, lang: str, delay: float) -> str:
    meme_id = payload.get("reddit_id", "")
    if not meme_id:
        return "skip:no_id"

    if await already_translated(meme_id, lang):
        return "skip:exists"

    fields = {
        "core_joke": payload.get("core_joke", ""),
        "psychological_state": payload.get("psychological_state", ""),
        "subtext_context": payload.get("subtext_context", ""),
        "search_dense_explanations": payload.get("search_dense_explanations", ""),
    }

    translated = await _with_retry(lambda: translate_caption(fields, lang))

    await neo4j_upsert_caption(
        meme_id=meme_id,
        lang=lang,
        core_joke=translated.get("core_joke", fields["core_joke"]),
        psychological_state=translated.get("psychological_state", fields["psychological_state"]),
        subtext_context=translated.get("subtext_context", fields["subtext_context"]),
        search_dense_explanations=translated.get("search_dense_explanations", fields["search_dense_explanations"]),
    )

    if delay > 0:
        await asyncio.sleep(delay)

    return "ok"


async def run(langs: list[str], delay: float, limit: int | None) -> None:
    payloads = await scroll_all_payloads()
    if limit:
        payloads = payloads[:limit]

    print(f"Found {len(payloads)} memes. Translating into: {', '.join(langs)}")

    for lang in langs:
        lang_name = SUPPORTED_LANGUAGES[lang]
        ok = skipped = errors = 0
        for i, payload in enumerate(payloads):
            meme_id = payload.get("reddit_id", f"#{i}")
            status = "error"
            try:
                if lang == "en":
                    if await already_translated(meme_id, "en"):
                        status = "skip:exists"
                        skipped += 1
                    else:
                        await neo4j_upsert_caption(
                            meme_id=meme_id,
                            lang="en",
                            core_joke=payload.get("core_joke", ""),
                            psychological_state=payload.get("psychological_state", ""),
                            subtext_context=payload.get("subtext_context", ""),
                            search_dense_explanations=payload.get("search_dense_explanations", ""),
                        )
                        status = "ok"
                        ok += 1
                else:
                    status = await translate_one(payload, lang, delay)
                    if status == "ok":
                        ok += 1
                    else:
                        skipped += 1
            except Exception as e:
                errors += 1
                status = "error"
                print(f"  ERROR [{lang}] {meme_id}: {e}")
            print(f"  [{lang_name}] {i+1}/{len(payloads)} {meme_id} -> {status}")

        print(f"[{lang_name}] done — ok={ok} skipped={skipped} errors={errors}")

    await close_all()
    print("Translation complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate meme captions into multiple languages")
    parser.add_argument(
        "--langs",
        nargs="+",
        default=[l for l in SUPPORTED_LANGUAGES if l != "en"],
        choices=list(SUPPORTED_LANGUAGES.keys()),
        help="Languages to translate into (default: all non-English)",
    )
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between Mistral calls")
    parser.add_argument("--limit", type=int, default=None, help="Max memes to process")
    args = parser.parse_args()
    asyncio.run(run(args.langs, args.delay, args.limit))


if __name__ == "__main__":
    main()
