from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, model_validator


class MemeDecodeSchema(BaseModel):
    core_joke: str = Field(min_length=1, max_length=400, description="Central joke or humorous observation")
    psychological_state: str = Field(min_length=1, max_length=120, description="Emotional or mental state depicted")
    subtext_context: str = Field(min_length=1, max_length=240, description="Cultural or situational subtext")
    search_dense_explanations: str = Field(min_length=40, max_length=800, description="Detailed searchable explanation")


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
    q: str = Field(min_length=1, max_length=400, description="Search query text")
    k: int = Field(default=20, ge=1, le=100, description="Number of results to return")
    visual_weight: float = Field(default=0.35, ge=0.0, le=1.0, description="Visual similarity weight")
    irony_weight: float = Field(default=0.65, ge=0.0, le=1.0, description="Irony/semantic similarity weight")
    template: str | None = Field(default=None, description="Filter by meme template")
    psychological_state: str | None = Field(default=None, description="Filter by psychological state")
    lang: str = Field(default="en", description="Caption language: en, es, fr, ja, pt")

    @model_validator(mode="after")
    def weights_must_sum_positive(self) -> SearchQueryParams:
        if self.visual_weight + self.irony_weight <= 0:
            raise ValueError("visual_weight + irony_weight must be greater than 0")
        return self


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
    lang: str = "en"
    lineage: LineageNode


class SearchResponse(BaseModel):
    query: str
    count: int
    weights: dict[Literal["visual", "irony"], float]
    results: list[MemeHit]
