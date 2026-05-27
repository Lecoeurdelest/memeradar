from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import models

from backend import config
from backend.clients import get_qdrant, mistral_embed, neo4j_lineage, tl_embed_text


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
) -> tuple[list[dict], Weights]:
    w = (weights or Weights()).normalized()

    visual_q, irony_q = await _embed_query(query)

    qfilter = _build_filter(template_filter, psychological_state_filter)

    client = get_qdrant()
    res = await client.query_points(
        collection_name=config.QDRANT_COLLECTION,
        prefetch=[
            models.Prefetch(
                query=visual_q,
                using="visual",
                limit=_candidates_per_space(w.visual, k),
                filter=qfilter,
            ),
            models.Prefetch(
                query=irony_q,
                using="irony",
                limit=_candidates_per_space(w.irony, k),
                filter=qfilter,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=k,
        with_payload=True,
    )

    results = []
    for p in res.points:
        lineage = await neo4j_lineage(p.payload["reddit_id"])
        results.append({
            "id": str(p.id),
            "score": p.score,
            "title": p.payload.get("title", ""),
            "image_url": p.payload.get("image_url", ""),
            "permalink": p.payload.get("permalink", ""),
            "upvotes": p.payload.get("upvotes", 0),
            "template": p.payload.get("template", ""),
            "core_joke": p.payload.get("core_joke", ""),
            "psychological_state": p.payload.get("psychological_state", ""),
            "subtext_context": p.payload.get("subtext_context", ""),
            "lineage": lineage,
        })

    return results, w


async def _embed_query(query: str) -> tuple[list[float], list[float]]:
    visual_q = await tl_embed_text(query)
    irony_q = await mistral_embed(query)
    return visual_q, irony_q


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
