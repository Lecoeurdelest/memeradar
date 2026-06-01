from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import config
from backend.clients import (
    close_all,
    ensure_mutation_indexes,
    neo4j_get_template_centroid,
    neo4j_set_template_centroid,
    qdrant_distinct_templates,
    qdrant_scroll_template_members,
    qdrant_set_payload_fields,
)
from backend.mutation import cosine_distance, spherical_mean

SECONDS_PER_DAY = 86400


async def _apply_member_drift(members, centroid, trending, concurrency):
    semaphore = asyncio.Semaphore(concurrency)

    async def _one(member):
        async with semaphore:
            vector = member.get("visual")
            if not vector:
                return
            drift = cosine_distance(vector, centroid)
            await qdrant_set_payload_fields(
                member["id"],
                {"template_drift_score": drift, "trending_mutation": trending},
            )

    await asyncio.gather(*(_one(m) for m in members))


async def _force_not_trending(members, concurrency):
    semaphore = asyncio.Semaphore(concurrency)

    async def _one(member):
        async with semaphore:
            await qdrant_set_payload_fields(member["id"], {"trending_mutation": False})

    await asyncio.gather(*(_one(m) for m in members))


def _resolve_historical(prior, now):
    if not prior:
        return None
    prior_centroid = prior.get("centroid_visual")
    prior_at = prior.get("centroid_computed_at")
    window = config.MUTATION_HISTORICAL_WINDOW_DAYS * SECONDS_PER_DAY
    if prior_centroid and prior_at is not None and (now - int(prior_at)) >= window:
        return prior_centroid
    return prior.get("historical_centroid_visual")


async def process_template(template, now, concurrency):
    members = await qdrant_scroll_template_members(template, config.MUTATION_SCROLL_BATCH)
    vectors = [m["visual"] for m in members if m.get("visual")]
    member_count = len(vectors)

    if member_count < config.MUTATION_MIN_MEMBERS:
        await neo4j_set_template_centroid(
            template=template,
            centroid_visual=None,
            historical_centroid_visual=None,
            velocity=0.0,
            computed_at=now,
            member_count=member_count,
        )
        await _force_not_trending(members, concurrency)
        return {"members": member_count, "velocity": 0.0, "trending": False, "status": "accumulating_baseline"}

    centroid = spherical_mean(vectors)
    historical = _resolve_historical(await neo4j_get_template_centroid(template), now)
    velocity = cosine_distance(centroid, historical) if historical else 0.0
    trending = velocity > config.MUTATION_VELOCITY_THRESHOLD

    await neo4j_set_template_centroid(
        template=template,
        centroid_visual=centroid,
        historical_centroid_visual=historical,
        velocity=velocity,
        computed_at=now,
        member_count=member_count,
    )
    await _apply_member_drift(members, centroid, trending, concurrency)
    return {"members": member_count, "velocity": round(velocity, 6), "trending": trending, "status": "computed"}


async def run(concurrency, limit):
    await ensure_mutation_indexes()
    templates = await qdrant_distinct_templates(config.MUTATION_SCROLL_BATCH)
    if limit:
        templates = templates[:limit]

    now = int(time.time())
    print(
        f"Mutation radar: {len(templates)} templates "
        f"(min_members={config.MUTATION_MIN_MEMBERS}, threshold={config.MUTATION_VELOCITY_THRESHOLD}, "
        f"window={config.MUTATION_HISTORICAL_WINDOW_DAYS}d)"
    )

    summary = {"computed": 0, "accumulating": 0, "trending": 0, "errors": 0}
    for i, template in enumerate(templates):
        try:
            result = await process_template(template, now, concurrency)
        except Exception as exc:
            summary["errors"] += 1
            print(f"  [{i + 1}/{len(templates)}] {template} -> ERROR {exc}")
            continue
        if result["status"] == "accumulating_baseline":
            summary["accumulating"] += 1
        else:
            summary["computed"] += 1
        if result["trending"]:
            summary["trending"] += 1
        print(
            f"  [{i + 1}/{len(templates)}] {template} -> members={result['members']} "
            f"velocity={result['velocity']} trending={result['trending']} ({result['status']})"
        )

    print(
        f"Done. computed={summary['computed']} accumulating={summary['accumulating']} "
        f"trending={summary['trending']} errors={summary['errors']}"
    )
    await close_all()


def main():
    parser = argparse.ArgumentParser(description="Compute meme mutation radar metrics per template")
    parser.add_argument("--concurrency", type=int, default=config.MUTATION_UPSERT_CONCURRENCY)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(run(args.concurrency, args.limit))


if __name__ == "__main__":
    main()
