# CLAUDE.md — Architectural Blueprints & Engineering Constraints

> This document defines system boundaries, data contracts, and discipline rules for the MemeRadar codebase.
>
> Cross-references: [README.md](README.md) · [TASKS.md](TASKS.md) · [TESTS.md](TESTS.md)

---

## 1. Repository File Tree

Every module, endpoint, and asset is enumerated below. New files require a corresponding task in [TASKS.md](TASKS.md) and at least one test in [TESTS.md](TESTS.md).

```
memeradar/
├── README.md                       # Operational manual — see [README.md](README.md)
├── CLAUDE.md                       # This file
├── TASKS.md                        # Sprint board — see [TASKS.md](TASKS.md)
├── TESTS.md                        # QA matrix — see [TESTS.md](TESTS.md)
│
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry; mounts /static and routes
│   ├── config.py                   # .env loader + fail-fast validation
│   ├── clients.py                  # Singletons: Qdrant, Twelve Labs, Mistral, Neo4j
│   ├── decoder.py                  # Mistral structured meme decoder
│   ├── ingest.py                   # Async ingestion pipeline orchestrator
│   ├── search.py                   # Universal Query API + RRF fusion logic
│   ├── enrich_cognee.py            # Post-ingest knowledge-graph enrichment
│   ├── schemas.py                  # Pydantic V2 contracts (see §2)
│   ├── requirements.txt
│   └── .env.example
│
├── scripts/
│   ├── crawl_reddit.py             # PRAW-based meme harvester
│   └── rrf_sweep.py                # CI-grade RRF rank-shift validator
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                 # Search bar + grid + weight slider + lineage panel
│       ├── App.css
│       └── api.js                  # Typed fetch wrapper for FastAPI /search
│
└── data/                           # Local asset mount (not committed)
    ├── images/                     # Scraped meme media
    └── memes.json                  # Crawl manifest
```

### 1.1 Endpoint Inventory

| Method | Path | Module | Purpose | Spec ref |
|---|---|---|---|---|
| `GET` | `/health` | `backend/main.py` | Liveness probe | [§2.3](#23-fastapi-search-schema) |
| `GET` | `/search` | `backend/main.py` → `backend/search.py` | RRF-fused multi-vector search | [§2.3](#23-fastapi-search-schema) |
| `GET` | `/static/images/{filename}` | `backend/main.py` (StaticFiles) | Public image mount for Twelve Labs fetch | [§3.4](#3-system-rules--engineering-constraints) |

---

## 2. Interface & Data Specifications

Pydantic V2 schemas are the source of truth. No implementation logic appears below — only structural contracts.

### 2.1 Mistral Decoder Output Schema

Produced by `backend/decoder.py`. Consumed by `backend/ingest.py` (writes payload to Qdrant) and the `/search` response (passes through to UI).

```python
class MemeDecodeSchema(BaseModel):
    core_joke: str = Field(min_length=1, max_length=400)
    psychological_state: str = Field(min_length=1, max_length=120)
    subtext_context: str = Field(min_length=1, max_length=240)
    search_dense_explanations: str = Field(min_length=40, max_length=800)
```

Field semantics:

| Field | Source | Used as | Tested by |
|---|---|---|---|
| `core_joke` | Mistral chat (JSON mode) | UI label + Neo4j `Meme.irony` property | [TESTS.md TC-LLM-001](TESTS.md#1-pipeline-extraction-tests) |
| `psychological_state` | Mistral chat | Filterable Qdrant payload facet | [TESTS.md TC-LLM-002](TESTS.md#1-pipeline-extraction-tests) |
| `subtext_context` | Mistral chat | Filterable Qdrant payload facet | [TESTS.md TC-LLM-003](TESTS.md#1-pipeline-extraction-tests) |
| `search_dense_explanations` | Mistral chat | Embedded by `mistral-embed` → `irony` vector | [TESTS.md TC-LLM-004](TESTS.md#1-pipeline-extraction-tests) |

Failure-mode contract: if Mistral returns invalid JSON, the decoder MUST raise `DecodeError` and the calling ingest task MUST be quarantined (not retried inline). See [TESTS.md TC-LLM-005 Malformed JSON Recovery](TESTS.md#1-pipeline-extraction-tests).

### 2.2 Qdrant Named Vector Point Mapping

Collection name: `memeradar` (configurable). Defined and materialized by `backend/clients.py::ensure_collection`.

```python
class QdrantVectorConfig(BaseModel):
    visual: NamedVectorParams      # size=1024, distance=COSINE  (Twelve Labs Marengo)
    irony:  NamedVectorParams      # size=1024, distance=COSINE  (Mistral-embed)


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


class QdrantPoint(BaseModel):
    id: UUID                       # uuid5(NAMESPACE_URL, reddit_id) — deterministic
    vector: dict[Literal["visual", "irony"], list[float]]
    payload: QdrantPointPayload
```

Indexes required at collection creation:

| Payload field | Index type | Purpose |
|---|---|---|
| `template` | KEYWORD | Hard filter chips in UI |
| `psychological_state` | KEYWORD | Facet filter |
| `subtext_context` | KEYWORD | Facet filter |
| `source_subreddit` | KEYWORD | Multi-subreddit mode |
| `upvotes` | INTEGER | Range filter / sort |

Tested by [TESTS.md TC-VEC-001 / TC-VEC-002](TESTS.md#2-vector-search-fusion-tests).

### 2.3 FastAPI `/search` Schema

Defined in `backend/schemas.py`, surfaced through `backend/main.py`.

```python
class SearchQueryParams(BaseModel):
    q: str = Field(min_length=1, max_length=400)
    k: int = Field(default=20, ge=1, le=100)
    visual_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    irony_weight:  float = Field(default=0.65, ge=0.0, le=1.0)
    template: str | None = None
    psychological_state: str | None = None

    @model_validator(mode="after")
    def weights_must_sum_positive(self) -> "SearchQueryParams": ...


class LineageNode(BaseModel):
    template: str
    variants: list[str]


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
```

Response invariants:

1. `len(response.results) == response.count ≤ params.k`
2. `response.results[i].score ≥ response.results[i+1].score` (sorted by RRF score desc)
3. `response.weights` reflects the *normalized* values actually applied, not the raw inputs.
4. Empty results return `count: 0, results: []` — never 404. Contract enforced by [TESTS.md TC-RRF-007](TESTS.md#2-vector-search-fusion-tests).

---

## 3. System Rules & Engineering Constraints

These are hard rules, not guidelines. CI gates on them.

### 3.1 Comment & Docstring Prohibition (Application Code)

Application code under `backend/` and `scripts/` MUST NOT contain:

- Inline comments (`# ...` at end of line)
- Block comments (`# ...` on their own line)
- Docstrings (triple-quoted strings as the first statement of a module, class, or function)

Exemptions (whitelisted):

- `backend/schemas.py` — Pydantic `Field(description=...)` is permitted; docstrings still forbidden.
- `requirements.txt` and `.env.example` may carry comments.
- Markdown files (`*.md`) are unaffected.
- Test files in any future `tests/` directory may use docstrings as test names.

Rationale: discipline forcing names to be self-documenting; reduces drift between comment and code; aligns with the "no superfluous prose" stance in [TASKS.md Definition of Done](TASKS.md#definition-of-done).

Enforcement: linter rule `application-no-comments` runs in CI. Verified by [TESTS.md TC-DISC-001](TESTS.md#5-discipline--code-quality-gates).

### 3.2 Async Processing Loops

All I/O-bound work crossing the network boundary MUST be expressed via explicit async primitives:

- `backend/ingest.py` uses `asyncio.gather` with a bounded `asyncio.Semaphore(N_WORKERS)` for the per-meme task fan-out. `ThreadPoolExecutor` is permitted ONLY for CPU-bound Tesseract calls wrapped in `asyncio.to_thread`.
- `backend/search.py` declares `async def search(...)` and awaits Qdrant/Neo4j clients.
- `backend/main.py` route handlers are `async def`.
- Synchronous SDK calls are wrapped in `asyncio.to_thread` (not run blocking on the event loop).

Verified by [TESTS.md TC-DISC-002 Async Audit](TESTS.md#5-discipline--code-quality-gates) and [TESTS.md TC-PERF-001](TESTS.md#5-discipline--code-quality-gates).

### 3.3 Determinism & Idempotency

- Qdrant point ID = `uuid5(NAMESPACE_URL, reddit_id)`. Re-running ingest on the same `memes.json` MUST be a no-op (no duplicates, no orphan points).
- Neo4j upserts use `MERGE`, never `CREATE`. Validated by [TESTS.md TC-GRAPH-003](TESTS.md#3-graph-lineage-validation).
- Crawler checkpoints `data/memes.json` every 25 posts to survive interruption.

### 3.4 Configuration Loading

- All secrets and runtime configuration enter the process exclusively via `backend/config.py`.
- Missing `REQUIRED` vars MUST cause boot to fail with a single, human-readable error listing all missing keys — no partial startup.
- The required/optional matrix is enumerated in [README.md §2](README.md#2-environment-configuration-interface).

### 3.5 No Docker

No `Dockerfile`, `docker-compose.yml`, or `.dockerignore` may exist in the repo. Datastores are native binaries managed by the operator per [README.md §1](README.md#1-system-prerequisites-installation-matrix).

### 3.6 Vendor Boundaries

Each vendor SDK is touched in exactly ONE module:

| Vendor | Owning module | Anywhere else? |
|---|---|---|
| Twelve Labs | `backend/clients.py` | Forbidden |
| Mistral | `backend/clients.py` + `backend/decoder.py` | Forbidden |
| Qdrant | `backend/clients.py` + `backend/search.py` | Forbidden |
| Neo4j | `backend/clients.py` | Forbidden |
| Cognee | `backend/enrich_cognee.py` | Forbidden |
| PRAW | `scripts/crawl_reddit.py` | Forbidden |

Verified by [TESTS.md TC-DISC-003 Vendor Containment](TESTS.md#5-discipline--code-quality-gates).
