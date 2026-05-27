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

- [ ] **T-2.5.1** — `scripts/rrf_sweep.py` hits `/search` with 5 weight pairs (1.0/0.0 → 0.0/1.0) and emits Jaccard matrix + JSON report. ← NEXT
  - Spec: [README.md §4.4](README.md#44-validation-script-hook)
  - Test: [TC-DEMO-001](TESTS.md#2-vector-search-fusion-tests), [TC-DEMO-002](TESTS.md#2-vector-search-fusion-tests)
- [ ] **T-2.5.2** — Exit code contract: 0 only if assertions in [README.md §4.3](README.md#43-rrf-validation-assertions) hold.
  - Spec: [README.md §4.3](README.md#43-rrf-validation-assertions)
  - Test: [TC-DEMO-003](TESTS.md#2-vector-search-fusion-tests)

**Sprint 2 exit criteria**: `curl /search?q=...` returns at least 5 results with non-null `lineage`; `scripts/rrf_sweep.py` exits 0 on the demo query; all Sprint 2 tests green.

---

## Sprint 3 — UI Delivery & Integration (Days 7-8)

Goal: judges can use the system. Demo video can be recorded.

### Feature F-3.1 — React shell

- [ ] **T-3.1.1** — Vite + React scaffold; `src/api.js` is a typed wrapper over `/search`.
  - Spec: [CLAUDE.md §1](CLAUDE.md#1-repository-file-tree)
  - Test: [TC-UI-001](TESTS.md#4-live-ui-integration-tests)
- [ ] **T-3.1.2** — Search bar + image grid (responsive `auto-fill, minmax(220px, 1fr)`).
  - Spec: [CLAUDE.md §1 frontend tree](CLAUDE.md#1-repository-file-tree)
  - Test: [TC-UI-002](TESTS.md#4-live-ui-integration-tests)

### Feature F-3.2 — Weight slider + RRF visibility

- [ ] **T-3.2.1** — Single slider binding `visual` (0..1) and computing `irony = 1 - visual` live; debounced refetch.
  - Spec: [README.md §4](README.md#4-live-demo--rrf-validation-script)
  - Test: [TC-UI-003](TESTS.md#4-live-ui-integration-tests), [TC-DEMO-004](TESTS.md#4-live-ui-integration-tests)
- [ ] **T-3.2.2** — Result tile shows `template` + `score`; click opens detail modal with `core_joke`, `psychological_state`, `subtext_context`, lineage.
  - Spec: [CLAUDE.md §2.3 MemeHit](CLAUDE.md#23-fastapi-search-schema)
  - Test: [TC-UI-004](TESTS.md#4-live-ui-integration-tests)

### Feature F-3.3 — Failure surfaces

- [ ] **T-3.3.1** — Empty state ("no memes match") when `count == 0`. No raw error in UI.
  - Spec: [CLAUDE.md §2.3 invariant 4](CLAUDE.md#23-fastapi-search-schema)
  - Test: [TC-UI-005](TESTS.md#4-live-ui-integration-tests), [TC-FAIL-003](TESTS.md#6-failure-boundary-assertions)
- [ ] **T-3.3.2** — Backend 5xx surfaces a toast, not a blank grid.
  - Spec: [CLAUDE.md §3.4](CLAUDE.md#34-configuration-loading)
  - Test: [TC-UI-006](TESTS.md#4-live-ui-integration-tests)

### Feature F-3.4 — Demo capture

- [ ] **T-3.4.1** — Record the 3-min demo following the [README.md §4 script](README.md#4-live-demo--rrf-validation-script).
  - Spec: [README.md §4](README.md#4-live-demo--rrf-validation-script)
  - Test: [TC-DEMO-005](TESTS.md#4-live-ui-integration-tests)
- [ ] **T-3.4.2** — README badges (build, demo video, hackathon track) and screenshot at top.
  - Spec: [README.md](README.md)
  - Test: not required.

**Sprint 3 exit criteria**: full demo can be performed live on a fresh laptop in under 5 minutes from `git clone`; all tests in [TESTS.md](TESTS.md) green.

---

## Cross-Cutting (Spans All Sprints)

- [ ] **T-X.1** — CI runs lint + test matrix on every PR. Lint includes the no-comments check from [CLAUDE.md §3.1](CLAUDE.md#31-comment--docstring-prohibition-application-code).
  - Test: [TC-DISC-001](TESTS.md#5-discipline--code-quality-gates)
- [ ] **T-X.2** — Vendor containment audit script — fails build if a forbidden import appears outside its owning module per [CLAUDE.md §3.6](CLAUDE.md#36-vendor-boundaries).
  - Test: [TC-DISC-003](TESTS.md#5-discipline--code-quality-gates)
