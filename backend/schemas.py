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
    image_sha256: str | None = Field(default=None, description="SHA-256 of the source image bytes; populated for user uploads")
    indexed_at: int | None = Field(default=None, description="Unix timestamp when the point was ingested; integer-indexed for mutation-radar time windows")
    template_drift_score: float | None = Field(default=None, description="Cosine distance of this meme's visual vector from its template spherical-mean centroid; written by the mutation-radar batch step")
    trending_mutation: bool = Field(default=False, description="Boolean filter flag raised by the mutation-radar batch step when the template drift velocity exceeds the experimental threshold")


class SearchQueryParams(BaseModel):
    q: str = Field(min_length=1, max_length=400, description="Search query text")
    k: int = Field(default=20, ge=1, le=100, description="Number of results to return")
    visual_weight: float = Field(default=0.35, ge=0.0, le=1.0, description="Visual similarity weight")
    irony_weight: float = Field(default=0.65, ge=0.0, le=1.0, description="Irony/semantic similarity weight")
    template: str | None = Field(default=None, description="Filter by meme template")
    psychological_state: str | None = Field(default=None, description="Filter by psychological state")
    lang: str = Field(default="en", pattern="^(en|es|fr|ja|pt|vi)$", description="Caption language: en, es, fr, ja, pt, vi")

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
    image_url: str
    permalink: str
    upvotes: int
    template: str
    core_joke: str
    psychological_state: str
    subtext_context: str
    lang: str = "en"
    lineage: LineageNode
    template_drift_score: float | None = None
    trending_mutation: bool = False


class SearchResponse(BaseModel):
    query: str
    count: int
    weights: dict[Literal["visual", "irony"], float]
    results: list[MemeHit]


class TemplateMutation(BaseModel):
    template: str
    member_count: int
    velocity: float
    trending_mutation: bool
    accumulating_baseline: bool


class MutationRadarResponse(BaseModel):
    count: int
    threshold: float
    min_members: int
    templates: list[TemplateMutation]


class UploadCheckResponse(BaseModel):
    image_sha256: str
    stored_path: str
    is_exact_duplicate: bool
    is_likely_duplicate: bool
    best_score: float
    matches: list[MemeHit]


class UploadIngestRequest(BaseModel):
    image_sha256: str = Field(min_length=64, max_length=64, pattern="^[0-9a-f]{64}$", description="Lowercase hex SHA-256 returned by /upload/check")
    title: str | None = Field(default=None, max_length=200, description="Optional human-supplied title")
