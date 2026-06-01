# TASKS.md — Sprint Plan & Multi-tier Progress Tracker

> 8-day execution across three sprints. Every task points to a spec in [CLAUDE.md](CLAUDE.md) and a test in [TESTS.md](TESTS.md).
>
> Companion documents: [README.md](README.md) · [CLAUDE.md](CLAUDE.md) · [TESTS.md](TESTS.md)

---

## Team & Cadence

| Role | Count | Primary lane |
|---|---|---|
| AI Researcher | 1 | Decoder prompt tuning, embedding strategy, RRF weight calibration |
| Software Engineer | 3 | Backend pipeline, search engine, frontend, CI |

Daily standup at 09:00, async write-up in `#memeradar-standup`. Sprint review at the end of each sprint window.

## Definition of Done

A task is `[x]` only when:

1. Implementation merged.
2. Specified test cases in [TESTS.md](TESTS.md) pass locally.
3. Code obeys [CLAUDE.md §3 System Rules](CLAUDE.md#3-system-rules--engineering-constraints), specifically the no-comment and async-loop rules.
4. No new vendor SDK touched outside its owning module — see [CLAUDE.md §3.6](CLAUDE.md#36-vendor-boundaries).

---

## Sprint 1 — Ingestion & Storage (Days 1-3)

Goal: 1000 memes scraped, decoded, vectorized, and queryable in Qdrant + Neo4j.

### Feature F-1.1 — Local infrastructure bootstrap

- [ ] **T-1.1.1** — Author `README.md §1 Prerequisites` and verify on a fresh macOS box.
  - Spec: [README.md §1.1](README.md#11-macos-homebrew)
  - Test: [TC-ENV-001](TESTS.md#1-pipeline-extraction-tests)
- [ ] **T-1.1.2** — Verify the same on a fresh Ubuntu 22.04 box.
  - Spec: [README.md §1.2](README.md#12-ubuntu-linux-apt)
  - Test: [TC-ENV-001](TESTS.md#1-pipeline-extraction-tests)
- [x] **T-1.1.3** — Author `.env.example` covering every key in the configuration matrix.
  - Spec: [README.md §2](README.md#2-environment-configuration-interface), [CLAUDE.md §3.4](CLAUDE.md#34-configuration-loading)
  - Test: [TC-ENV-002](TESTS.md#1-pipeline-extraction-tests)

### Feature F-1.2 — Reddit crawler

- [x] **T-1.2.1** — Implement `scripts/crawl_reddit.py` with PRAW + checkpointing every 25 posts.
  - Spec: [CLAUDE.md §1](CLAUDE.md#1-repository-file-tree), [CLAUDE.md §3.3](CLAUDE.md#33-determinism--idempotency)
  - Test: [TC-CRAWL-001](TESTS.md#1-pipeline-extraction-tests), [TC-CRAWL-002](TESTS.md#1-pipeline-extraction-tests)
- [x] **T-1.2.2** — URL resolver covering `i.redd.it`, `imgur`, and Reddit preview fallback.
  - Spec: [CLAUDE.md §1](CLAUDE.md#1-repository-file-tree)
  - Test: [TC-CRAWL-003](TESTS.md#1-pipeline-extraction-tests)
- [x] **T-1.2.3** — Filter NSFW, self-posts, and non-image submissions.
  - Spec: [CLAUDE.md §1](CLAUDE.md#1-repository-file-tree)
  - Test: [TC-CRAWL-004](TESTS.md#1-pipeline-extraction-tests)

### Feature F-1.3 — Mistral structured decoder

- [x] **T-1.3.1** — Implement `backend/decoder.py` with JSON-mode prompt returning the four fields specified in [CLAUDE.md §2.1](CLAUDE.md#21-mistral-decoder-output-schema).
  - Spec: [CLAUDE.md §2.1](CLAUDE.md#21-mistral-decoder-output-schema)
  - Test: [TC-LLM-001](TESTS.md#1-pipeline-extraction-tests), [TC-LLM-002](TESTS.md#1-pipeline-extraction-tests), [TC-LLM-003](TESTS.md#1-pipeline-extraction-tests), [TC-LLM-004](TESTS.md#1-pipeline-extraction-tests)
- [x] **T-1.3.2** — Defensive JSON coercion: handle fenced output, prose-wrapped output, partial JSON.
  - Spec: [CLAUDE.md §2.1 failure-mode contract](CLAUDE.md#21-mistral-decoder-output-schema)
  - Test: [TC-LLM-005](TESTS.md#1-pipeline-extraction-tests)
- [x] **T-1.3.3** — Tesseract OCR wrapper with graceful `(no text)` fallback.
  - Spec: [CLAUDE.md §2.1](CLAUDE.md#21-mistral-decoder-output-schema)
  - Test: [TC-OCR-001](TESTS.md#1-pipeline-extraction-tests), [TC-OCR-002](TESTS.md#1-pipeline-extraction-tests)

### Feature F-1.4 — Vector + graph upsert

- [x] **T-1.4.1** — `backend/clients.py::ensure_collection` materializes the named-vector schema and payload indexes from [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping).
  - Spec: [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping)
  - Test: [TC-VEC-001](TESTS.md#2-vector-search-fusion-tests)
- [x] **T-1.4.2** — Deterministic `uuid5` point IDs; ingest is idempotent across reruns.
  - Spec: [CLAUDE.md §3.3](CLAUDE.md#33-determinism--idempotency)
  - Test: [TC-VEC-002](TESTS.md#2-vector-search-fusion-tests)
- [x] **T-1.4.3** — Neo4j `(Meme)-[:USES_TEMPLATE]->(MemeTemplate)` `MERGE` upsert.
  - Spec: [CLAUDE.md §3.3](CLAUDE.md#33-determinism--idempotency)
  - Test: [TC-GRAPH-001](TESTS.md#3-graph-lineage-validation), [TC-GRAPH-003](TESTS.md#3-graph-lineage-validation)
- [x] **T-1.4.4** — Async ingestion loop with bounded semaphore per [CLAUDE.md §3.2](CLAUDE.md#32-async-processing-loops).
  - Spec: [CLAUDE.md §3.2](CLAUDE.md#32-async-processing-loops)
  - Test: [TC-DISC-002](TESTS.md#5-discipline--code-quality-gates), [TC-PERF-001](TESTS.md#5-discipline--code-quality-gates)

### Feature F-1.5 — Knowledge-graph enrichment

- [x] **T-1.5.1** — `backend/enrich_cognee.py` post-pass reading `search_dense_explanations` corpus.
  - Spec: [CLAUDE.md §1 endpoint inventory](CLAUDE.md#11-endpoint-inventory)
  - Test: [TC-GRAPH-002](TESTS.md#3-graph-lineage-validation), [TC-GRAPH-004](TESTS.md#3-graph-lineage-validation)

**Sprint 1 exit criteria**: `python -m backend.ingest` finishes 1000 memes; Qdrant collection has 1000 points with both named vectors populated; Neo4j has at least 50 `MemeTemplate` nodes; all Sprint 1 tests green.

---

## Sprint 2 — Search Fusion Engine (Days 4-6)

Goal: `/search` endpoint returns RRF-fused results with Neo4j lineage. The demo's "wow" sweep must work end-to-end.

### Feature F-2.1 — Pydantic contracts

- [x] **T-2.1.1** — `backend/schemas.py` mirrors [CLAUDE.md §2.3](CLAUDE.md#23-fastapi-search-schema) exactly. Includes `SearchQueryParams`, `MemeHit`, `LineageNode`, `SearchResponse`. ✅
  - Spec: [CLAUDE.md §2.3](CLAUDE.md#23-fastapi-search-schema)
  - Test: [TC-API-001](TESTS.md#4-live-ui-integration-tests)
- [x] **T-2.1.2** — Weight validator (`model_validator`) ensures `visual_weight + irony_weight > 0`.
  - Spec: [CLAUDE.md §2.3 invariant 3](CLAUDE.md#23-fastapi-search-schema)
  - Test: [TC-API-002](TESTS.md#4-live-ui-integration-tests)

### Feature F-2.2 — Dual query embedding

- [x] **T-2.2.1** — Twelve Labs text embedding for visual-space query.
  - Spec: [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping)
  - Test: [TC-RRF-001](TESTS.md#2-vector-search-fusion-tests)
- [x] **T-2.2.2** — Mistral-embed for irony-space query.
  - Spec: [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping)
  - Test: [TC-RRF-002](TESTS.md#2-vector-search-fusion-tests)

### Feature F-2.3 — RRF fusion via Universal Query API

- [x] **T-2.3.1** — `backend/search.py` issues a single `query_points` with two prefetches and `FusionQuery(Fusion.RRF)`.
  - Spec: [CLAUDE.md §2.3](CLAUDE.md#23-fastapi-search-schema)
  - Test: [TC-RRF-003](TESTS.md#2-vector-search-fusion-tests), [TC-RRF-004](TESTS.md#2-vector-search-fusion-tests)
- [x] **T-2.3.2** — Weight-to-candidate-count translation function. Document the formula in `search.py` as a constant — no inline comment per [CLAUDE.md §3.1](CLAUDE.md#31-comment--docstring-prohibition-application-code).
  - Spec: [CLAUDE.md §3.1](CLAUDE.md#31-comment--docstring-prohibition-application-code)
  - Test: [TC-RRF-005](TESTS.md#2-vector-search-fusion-tests), [TC-RRF-006](TESTS.md#2-vector-search-fusion-tests)
- [x] **T-2.3.3** — Empty-result safety: returns `count: 0, results: []` not 404.
  - Spec: [CLAUDE.md §2.3 invariant 4](CLAUDE.md#23-fastapi-search-schema)
  - Test: [TC-RRF-007](TESTS.md#2-vector-search-fusion-tests)

### Feature F-2.4 — Lineage join

- [x] **T-2.4.1** — Per-result Neo4j Cypher `MATCH (m:Meme {id: $id})-[:USES_TEMPLATE]->(t)-[:VARIATION_OF*0..2]-(sib)` returning `LineageNode`.
  - Spec: [CLAUDE.md §2.3 MemeHit.lineage](CLAUDE.md#23-fastapi-search-schema)
  - Test: [TC-GRAPH-002](TESTS.md#3-graph-lineage-validation), [TC-GRAPH-005](TESTS.md#3-graph-lineage-validation)

### Feature F-2.5 — RRF rank-shift validator

- [x] **T-2.5.1** — `scripts/rrf_sweep.py` hits `/search` with 5 weight pairs (1.0/0.0 → 0.0/1.0) and emits Jaccard matrix + JSON report. ✅
  - Spec: [README.md §4.4](README.md#44-validation-script-hook)
  - Test: [TC-DEMO-001](TESTS.md#2-vector-search-fusion-tests), [TC-DEMO-002](TESTS.md#2-vector-search-fusion-tests)
- [x] **T-2.5.2** — Exit code contract: 0 only if assertions in [README.md §4.3](README.md#43-rrf-validation-assertions) hold. Extreme Jaccard = 0.0 confirmed. ✅
  - Spec: [README.md §4.3](README.md#43-rrf-validation-assertions)
  - Test: [TC-DEMO-003](TESTS.md#2-vector-search-fusion-tests)

**Sprint 2 exit criteria**: ✅ `/search` returns results with non-null lineage; `scripts/rrf_sweep.py` exits 0.

---

## Sprint 3 — UI Delivery & Integration (Days 7-8)

Goal: judges can use the system. Demo video can be recorded.

### Feature F-3.1 — React shell

- [x] **T-3.1.1** — Vite + React scaffold; `src/api.js` is a typed wrapper over `/search`. ✅
  - Spec: [CLAUDE.md §1](CLAUDE.md#1-repository-file-tree)
  - Test: [TC-UI-001](TESTS.md#4-live-ui-integration-tests)
- [x] **T-3.1.2** — Search bar + image grid (responsive `auto-fill, minmax(220px, 1fr)`). ✅
  - Spec: [CLAUDE.md §1 frontend tree](CLAUDE.md#1-repository-file-tree)
  - Test: [TC-UI-002](TESTS.md#4-live-ui-integration-tests)

### Feature F-3.2 — Weight slider + RRF visibility

- [x] **T-3.2.1** — Single slider binding `visual` (0..1) and computing `irony = 1 - visual` live; debounced refetch. ✅
  - Spec: [README.md §4](README.md#4-live-demo--rrf-validation-script)
  - Test: [TC-UI-003](TESTS.md#4-live-ui-integration-tests), [TC-DEMO-004](TESTS.md#4-live-ui-integration-tests)
- [x] **T-3.2.2** — Result tile shows `template` + `score`; click opens detail modal with `core_joke`, `psychological_state`, `subtext_context`, lineage. ✅
  - Spec: [CLAUDE.md §2.3 MemeHit](CLAUDE.md#23-fastapi-search-schema)
  - Test: [TC-UI-004](TESTS.md#4-live-ui-integration-tests)

### Feature F-3.3 — Failure surfaces

- [x] **T-3.3.1** — Empty state ("no memes match") when `count == 0`. No raw error in UI. ✅
  - Spec: [CLAUDE.md §2.3 invariant 4](CLAUDE.md#23-fastapi-search-schema)
  - Test: [TC-UI-005](TESTS.md#4-live-ui-integration-tests), [TC-FAIL-003](TESTS.md#6-failure-boundary-assertions)
- [x] **T-3.3.2** — Backend 5xx surfaces a toast, not a blank grid. ✅
  - Spec: [CLAUDE.md §3.4](CLAUDE.md#34-configuration-loading)
  - Test: [TC-UI-006](TESTS.md#4-live-ui-integration-tests)

### Feature F-3.4 — Demo capture

- [ ] **T-3.4.1** — Record the 3-min demo following the [README.md §4 script](README.md#4-live-demo--rrf-validation-script).
  - Spec: [README.md §4](README.md#4-live-demo--rrf-validation-script)
  - Test: [TC-DEMO-005](TESTS.md#4-live-ui-integration-tests)
- [ ] **T-3.4.2** — README badges (build, demo video, hackathon track) and screenshot at top.
  - Spec: [README.md](README.md)
  - Test: not required.

**Sprint 3 exit criteria**: ✅ Full UI functional; backend + frontend served from single port `:8000`.

---

## Sprint 4 — Multilingual Support

Goal: captions for every ingested meme translated into ES, FR, JA, PT, VI and stored in Neo4j. The `/search` endpoint accepts `lang` and returns translated captions. UI has a language picker.

**Supported languages**: `en` English · `es` Spanish · `fr` French · `ja` Japanese · `pt` Portuguese · `vi` Vietnamese

**Architecture**:
- Translations stored as `(:MemeCaption {lang})-[:HAS_CAPTION]-(m:Meme)` nodes in Neo4j
- `mistral-embed` is natively multilingual — no separate vectors per language needed
- Query-time: no translation of the user's query; Mistral's embedding model handles cross-lingual matching natively

### Feature F-4.1 — Translation module

- [x] **T-4.1.1** — `backend/translate.py` with `translate_caption(fields, target_lang)` using Mistral chat JSON-mode. Supports `SUPPORTED_LANGUAGES = {en, es, fr, ja, pt, vi}`. ✅
- [x] **T-4.1.2** — `backend/clients.py` gains `neo4j_upsert_caption(meme_id, lang, ...)` and `neo4j_get_caption(meme_id, lang)`. ✅
  - Graph model: `(m:Meme)-[:HAS_CAPTION]->(c:MemeCaption {lang, core_joke, psychological_state, subtext_context, search_dense_explanations})`

### Feature F-4.2 — Batch translation script

- [ ] **T-4.2.1** — `scripts/translate_captions.py` scrolls all Qdrant payloads, calls Mistral for each meme × language, upserts into Neo4j. Idempotent (skips already-translated nodes). Includes 429 retry backoff.
  - Run: `python scripts/translate_captions.py --langs es fr ja pt vi --delay 1.5`
- [ ] **T-4.2.2** — Verify every ingested meme has captions for all 5 non-English languages in Neo4j.
  - Check: Neo4j node count `MATCH (c:MemeCaption) RETURN c.lang, count(c)` → one row per lang, equal to the ingested meme count.

### Feature F-4.3 — Multilingual search endpoint

- [x] **T-4.3.1** — `/search` accepts `lang` query param (`en|es|fr|ja|pt|vi`, default `en`). ✅
- [x] **T-4.3.2** — When `lang != en` and translation exists in Neo4j, response `core_joke`, `psychological_state`, `subtext_context` are the translated values; falls back to English if not yet translated. ✅
- [x] **T-4.3.3** — `MemeHit` schema gains `lang: str` field. ✅

### Feature F-4.4 — Language picker UI

- [x] **T-4.4.1** — Language picker pill buttons (🇺🇸 🇪🇸 🇫🇷 🇯🇵 🇧🇷 🇻🇳) in the UI; switching re-fetches with new `lang` param. ✅
- [x] **T-4.4.2** — Modal captions reflect the selected language. ✅

**Sprint 4 exit criteria**: `python scripts/translate_captions.py` completes without error; `curl /search?q=cat&lang=ja` returns Japanese captions; UI language picker switches captions live.

---

## Sprint 5 — Meme Mutation Radar

Goal: quantify each template's semantic/visual "drift velocity" relative to its spherical-mean centroid over time, computed in a decoupled batch step so the hot search path never runs dense-vector arithmetic. Spec: [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping) (payload contract) + [implementation-notes.md](implementation-notes.md) (full KSP 1 contract and unspec'd decisions).

### Feature F-5.1 — Meme Mutation Radar Implementation

- [x] **Feature: Meme Mutation Radar Implementation** ✅ (live end-to-end verified 2026-06-01)
  - [x] **T-5.1.1** — Schema migration: Qdrant integer index on `indexed_at`, keyword index on `template`, float payload `template_drift_score`, boolean filter `trending_mutation`; Neo4j `:MemeTemplate` gains `centroid_visual`, `historical_centroid_visual`, `velocity`. Materialized by `backend/clients.py::ensure_mutation_indexes` (idempotent) + Neo4j upsert helpers.
    - Spec: [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping)
    - Test: [TC-VEC-003](TESTS.md#2-vector-search--fusion-tests)
  - [x] **T-5.1.2** — Background execution script `scripts/compute_mutation_metrics.py`: scroll template members via the `template` index, compute centroid, write `centroid_visual` to Neo4j, upsert per-point `template_drift_score` to Qdrant, and flip `trending_mutation` when 7-day drift velocity exceeds threshold. Strict async; bounded `Semaphore` over the per-member update pass per [CLAUDE.md §3.2](CLAUDE.md#32-async-processing-loops).
    - Spec: [CLAUDE.md §3.2](CLAUDE.md#32-async-processing-loops), [CLAUDE.md §3.6](CLAUDE.md#36-vendor-boundaries)
    - Test: [TC-VEC-003](TESTS.md#2-vector-search--fusion-tests), [TC-FAIL-009](TESTS.md#6-failure-boundary-assertions)
  - [x] **T-5.1.3** — Spherical-mean mathematics module `backend/mutation.py`: `normalize → mean → renormalize` producing a unit-length centroid; cosine distance with zero-vector guard. Pure math, no vendor SDK.
    - Spec: [CLAUDE.md §3.1](CLAUDE.md#31-comment--docstring-prohibition-application-code)
    - Test: [TC-VEC-003](TESTS.md#2-vector-search--fusion-tests)
  - [x] **T-5.1.4** — Small-sample guardrails: templates with `< MUTATION_MIN_MEMBERS` (5) force `velocity = 0.0` and `trending_mutation = false`, bypass velocity computation, and are flagged "accumulating baseline data".
    - Spec: [implementation-notes.md](implementation-notes.md)
    - Test: [TC-FAIL-009](TESTS.md#6-failure-boundary-assertions)

### Feature F-5.2 — Meme Mutation Radar Dashboard Panel (Frontend)

- [ ] **Frontend: Meme Mutation Radar Dashboard Panel** — Meme-detail side panel visualizing template drift, mutation velocity, and lineage from the pre-materialized `/mutations` cache. New modules: `frontend/src/components/MutationRadar.jsx` + `MutationRadar.css`; payload mappers added to `frontend/src/api.js`. Spec: [CLAUDE.md §1 frontend tree](CLAUDE.md#1-repository-file-tree), [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping). See [implementation-notes-ui.html](implementation-notes-ui.html).
  - [ ] **T-5.2.1** — UI asset binding: extend the `api.js` client layer to fetch `/mutations` and map `template_drift_score`, `trending_mutation`, and `lineage_cache` (`template`, `variants`) into a normalized radar model with null-lineage fallbacks.
    - Spec: [CLAUDE.md §2.3 invariant 5](CLAUDE.md#23-fastapi-search-schema)
    - Test: [TC-UI-008](TESTS.md#4-live-ui-integration-tests)
  - [ ] **T-5.2.2** — Trend Velocity badge component: prominent "Trending Mutation" (High Velocity) vs "Stable Format" badge driven by `trending_mutation`; Drift Vector gauge over the `0.0 (Canonical) → 1.0 (Extreme Drift)` range.
    - Spec: [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping)
    - Test: [TC-UI-008](TESTS.md#4-live-ui-integration-tests)
  - [ ] **T-5.2.3** — Small-sample banner logic: when the selected template is accumulating baseline (`member_count < MUTATION_MIN_MEMBERS`, surfaced as `velocity == 0.0`), replace the live velocity graph with the "Accumulating baseline data" notice.
    - Spec: [implementation-notes-ui.html](implementation-notes-ui.html)
    - Test: [TC-UI-007](TESTS.md#4-live-ui-integration-tests)
  - [ ] **T-5.2.4** — State integration: fetch the mutation index once on mount, derive the radar model from the selected meme, and degrade gracefully (null-lineage values) when `/mutations` errors per [CLAUDE.md §2.3 invariant 5](CLAUDE.md#23-fastapi-search-schema).
    - Spec: [CLAUDE.md §2.3 invariant 5](CLAUDE.md#23-fastapi-search-schema)
    - Test: [TC-UI-007](TESTS.md#4-live-ui-integration-tests), [TC-UI-008](TESTS.md#4-live-ui-integration-tests)

**Sprint 5 exit criteria**: ✅ `python scripts/compute_mutation_metrics.py` completes without error against a populated collection; `GET /mutations` returns per-template velocity with trending flags; `backend/mutation.py` emits a unit-length centroid (TC-VEC-003); small-sample templates default to zero velocity (TC-FAIL-009). **Met 2026-06-01** against live Qdrant Cloud (106 pts) + Neo4j Aura (103 templates): batch ran 0 errors, `/mutations` round-trip returned 103 accumulating templates, live centroid read-back L2==1.0. Computed/trending path verified via in-memory real-Qdrant integration + a MIN=1 live verification run (see [progress.md](progress.md)).

---

## Cross-Cutting (Spans All Sprints)

- [ ] **T-X.1** — CI runs lint + test matrix on every PR. Lint includes the no-comments check from [CLAUDE.md §3.1](CLAUDE.md#31-comment--docstring-prohibition-application-code).
  - Test: [TC-DISC-001](TESTS.md#5-discipline--code-quality-gates)
- [ ] **T-X.2** — Vendor containment audit script — fails build if a forbidden import appears outside its owning module per [CLAUDE.md §3.6](CLAUDE.md#36-vendor-boundaries).
  - Test: [TC-DISC-003](TESTS.md#5-discipline--code-quality-gates)
