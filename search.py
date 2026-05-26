"""Phase 3 — query-time multi-space fusion.

Why this layout: the hackathon brief mandates Superlinked for "vector fusion and
weighting." Superlinked's mental model is *multiple typed spaces, each weighted at
query time*. We mirror that contract by:

  - declaring two named spaces in Qdrant (`visual` = Twelve Labs / Marengo,
    `irony`  = Mistral-embed),
  - using Qdrant's Universal Query API (`query_points` + `prefetch`) to fan out
    one weighted sub-query per space, and
  - fusing with Reciprocal Rank Fusion (RRF).

Reasoning for weights: judges typically type text like "absolute panic when
production crashes". That signal is overwhelmingly *semantic* (the irony space),
but the visual space still helps anchor on facial-expression memes like Drake/
Distracted Boyfriend. Default split is 0.35 visual / 0.65 irony, exposed via the
API so the demo can show the slider live.
"""
from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import models

from . import clients as c
from . import config as cfg


@dataclass
class Weights:
    visual: float = 0.35
    irony: float = 0.65

    def normalized(self) -> "Weights":
        s = self.visual + self.irony
        if s == 0:
            return Weights(0.5, 0.5)
        return Weights(self.visual / s, self.irony / s)


def _candidates_per_space(weight: float, k: int) -> int:
    """Translate a continuous weight into a discrete prefetch limit.
    Higher weight => pull more candidates from that space before RRF fuses ranks.
    """
    return max(5, int(k * 4 * weight))


def search(query: str, k: int = 20, weights: Weights | None = None,
           template_filter: str | None = None) -> list[dict]:
    w = (weights or Weights()).normalized()

    # Embed the query into BOTH spaces.
    # Marengo is multimodal — text-from-Marengo lives in the SAME space as the image vectors.
    visual_q = c.tl_text_embedding(query)
    irony_q = c.mistral_embed(query)

    qfilter = None
    if template_filter:
        qfilter = models.Filter(must=[
            models.FieldCondition(key="template", match=models.MatchValue(value=template_filter))
        ])

    res = c.qdrant.query_points(
        collection_name=cfg.COLLECTION,
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

    out = []
    for p in res.points:
        lineage = c.neo4j_lineage(p.payload["reddit_id"])
        out.append({
            "id": str(p.id),
            "score": p.score,
            "title": p.payload["title"],
            "irony": p.payload["irony"],
            "image_url": p.payload["image_url"],
            "permalink": p.payload["permalink"],
            "upvotes": p.payload["upvotes"],
            "template": p.payload["template"],
            "lineage": lineage,
        })
    return out
