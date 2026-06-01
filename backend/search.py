from __future__ import annotations

import asyncio
from dataclasses import dataclass

from qdrant_client import models

from backend import config
from backend.clients import get_qdrant, mistral_embed, neo4j_get_caption, neo4j_lineage, tl_embed_text
from backend.translate import SUPPORTED_LANGUAGES


PREFETCH_FLOOR = 5
PREFETCH_MULTIPLIER = 4


@dataclass
class Weights:
    visual: float = 0.35
    irony: float = 0.65

    def normalized(self) -> Weights:
        s = self.visual + self.irony
        if s == 0:
            return Weights(0.5, 0.5)
        return Weights(self.visual / s, self.irony / s)


def _candidates_per_space(weight: float, k: int) -> int:
    return max(PREFETCH_FLOOR, int(k * PREFETCH_MULTIPLIER * weight))


async def search(
    query: str,
    k: int = 20,
    weights: Weights | None = None,
    template_filter: str | None = None,
    psychological_state_filter: str | None = None,
    lang: str = "en",
) -> tuple[list[dict], Weights]:
    w = (weights or Weights()).normalized()
    visual_q, irony_q = await _embed_query(query)
    results = await _query_by_vectors(
        visual_vec=visual_q,
        irony_vec=irony_q,
        k=k,
        weights=w,
        template_filter=template_filter,
        psychological_state_filter=psychological_state_filter,
        lang=lang,
    )
    return results, w


async def query_by_visual_vector(
    visual_vec: list[float],
    k: int,
    lang: str = "en",
) -> list[dict]:
    return await _query_by_vectors(
        visual_vec=visual_vec,
        irony_vec=None,
        k=k,
        weights=Weights(visual=1.0, irony=0.0),
        template_filter=None,
        psychological_state_filter=None,
        lang=lang,
    )


async def random_memes(k: int = 24, lang: str = "en") -> list[dict]:
    client = get_qdrant()
    res = await client.query_points(
        collection_name=config.QDRANT_COLLECTION,
        query=models.SampleQuery(sample=models.Sample.RANDOM),
        limit=k,
        with_payload=True,
    )
    results = await _assemble(res.points, lang)
    for r in results:
        r["score"] = 0.0
    return results


async def _query_by_vectors(
    visual_vec: list[float] | None,
    irony_vec: list[float] | None,
    k: int,
    weights: Weights,
    template_filter: str | None,
    psychological_state_filter: str | None,
    lang: str,
) -> list[dict]:
    qfilter = _build_filter(template_filter, psychological_state_filter)

    prefetches = []
    if visual_vec is not None and weights.visual > 0.01:
        prefetches.append(models.Prefetch(
            query=visual_vec,
            using="visual",
            limit=_candidates_per_space(weights.visual, k),
            filter=qfilter,
        ))
    if irony_vec is not None and weights.irony > 0.01:
        prefetches.append(models.Prefetch(
            query=irony_vec,
            using="irony",
            limit=_candidates_per_space(weights.irony, k),
            filter=qfilter,
        ))
    if not prefetches:
        if visual_vec is not None:
            prefetches.append(models.Prefetch(query=visual_vec, using="visual", limit=k, filter=qfilter))
        if irony_vec is not None:
            prefetches.append(models.Prefetch(query=irony_vec, using="irony", limit=k, filter=qfilter))
    if not prefetches:
        return []

    client = get_qdrant()

    if len(prefetches) == 1:
        only = prefetches[0]
        res = await client.query_points(
            collection_name=config.QDRANT_COLLECTION,
            query=only.query,
            using=only.using,
            query_filter=qfilter,
            limit=k,
            with_payload=True,
        )
    else:
        res = await client.query_points(
            collection_name=config.QDRANT_COLLECTION,
            prefetch=prefetches,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=k,
            with_payload=True,
        )

    return await _assemble(res.points, lang)


async def _assemble(points, lang: str) -> list[dict]:
    use_lang = lang if lang in SUPPORTED_LANGUAGES and lang != "en" else None

    meme_ids = [p.payload["reddit_id"] for p in points]
    lineages = await asyncio.gather(*(_safe_lineage(mid) for mid in meme_ids))
    if use_lang:
        captions = await asyncio.gather(*(_safe_caption(mid, use_lang) for mid in meme_ids))
    else:
        captions = [None] * len(meme_ids)

    results = []
    for p, lineage, caption in zip(points, lineages, captions):
        results.append({
            "id": str(p.id),
            "score": p.score,
            "title": p.payload.get("title", ""),
            "image_url": p.payload.get("image_url", ""),
            "permalink": p.payload.get("permalink", ""),
            "upvotes": p.payload.get("upvotes", 0),
            "template": p.payload.get("template", ""),
            "core_joke": (caption or {}).get("core_joke") or p.payload.get("core_joke", ""),
            "psychological_state": (caption or {}).get("psychological_state") or p.payload.get("psychological_state", ""),
            "subtext_context": (caption or {}).get("subtext_context") or p.payload.get("subtext_context", ""),
            "lang": lang,
            "lineage": lineage,
            "template_drift_score": p.payload.get("template_drift_score"),
            "trending_mutation": bool(p.payload.get("trending_mutation", False)),
        })

    return results


async def _safe_lineage(meme_id: str) -> dict:
    try:
        return await neo4j_lineage(meme_id)
    except Exception:
        return {"template": None, "variants": []}


async def _safe_caption(meme_id: str, lang: str) -> dict | None:
    try:
        return await neo4j_get_caption(meme_id, lang)
    except Exception:
        return None


async def _embed_query(query: str) -> tuple[list[float], list[float]]:
    visual_q = await tl_embed_text(query)
    delays = [2, 5, 10, 20]
    last_exc: Exception | None = None
    for attempt, delay in enumerate([0] + delays):
        if delay:
            await asyncio.sleep(delay)
        try:
            irony_q = await mistral_embed(query)
            return visual_q, irony_q
        except Exception as exc:
            last_exc = exc
            if "429" not in str(exc):
                raise
    assert last_exc is not None
    raise last_exc


def _build_filter(
    template: str | None,
    psychological_state: str | None,
) -> models.Filter | None:
    conditions = []
    if template:
        conditions.append(
            models.FieldCondition(key="template", match=models.MatchValue(value=template))
        )
    if psychological_state:
        conditions.append(
            models.FieldCondition(
                key="psychological_state",
                match=models.MatchValue(value=psychological_state),
            )
        )
    if not conditions:
        return None
    return models.Filter(must=conditions)