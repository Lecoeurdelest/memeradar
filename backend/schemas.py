from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class MemeDecodeSchema(BaseModel):
    core_joke: str = Field(min_length=1, max_length=400)
    psychological_state: str = Field(min_length=1, max_length=120)
    subtext_context: str = Field(min_length=1, max_length=240)
    search_dense_explanations: str = Field(min_length=40, max_length=800)


class QdrantPointPayload(BaseModel):
    reddit_id: str
    title: str
    ocr_text: str
    image_url: HttpUrl
    permalink: HttpUrl
    upvotes: int = Field(ge=0)
    source_subreddit: str
    template: str = Field(max_length=64)
    core_joke: str
    psychological_state: str
    subtext_context: str
    search_dense_explanations: str


class SearchQueryParams(BaseModel):
    q: str = Field(min_length=1, max_length=400)
    k: int = Field(default=20, ge=1, le=100)
    visual_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    irony_weight: float = Field(default=0.65, ge=0.0, le=1.0)
    template: str | None = None
    psychological_state: str | None = None


class LineageNode(BaseModel):
    template: str | None = None
    variants: list[str] = []


class MemeHit(BaseModel):
    id: UUID
    score: float
    title: str
    image_url: HttpUrl
    permalink: HttpUrl
    upvotes: int
    template: str
    core_joke: str
    psychological_state: str
    subtext_context: str
    lineage: LineageNode


class SearchResponse(BaseModel):
    query: str
    count: int
    weights: dict[Literal["visual", "irony"], float]
    results: list[MemeHit]
