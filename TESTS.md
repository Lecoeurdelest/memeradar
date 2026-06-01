# TESTS.md — Traceability QA Matrix
 
> End-to-end test playbook. Every case maps back to a task in [TASKS.md](TASKS.md) and a spec in [CLAUDE.md](CLAUDE.md).
>
> Companion documents: [README.md](README.md) · [CLAUDE.md](CLAUDE.md) · [TASKS.md](TASKS.md)
 
---
 
## Conventions
 
- Status: `[ ]` not yet verified · `[x]` passing on current main.
- ID prefix indicates suite: `ENV`, `CRAWL`, `OCR`, `LLM`, `ING`, `VEC`, `RRF`, `GRAPH`, `API`, `UI`, `DEMO`, `DISC`, `PERF`, `FAIL`.
- Severity: `P0` blocks demo · `P1` degrades demo · `P2` quality polish.
- Type: `Unit` · `Integration` · `Manual` · `Boundary`.
- A test flips to `[x]` only when its `Asserts` line holds AND its linked task in [TASKS.md](TASKS.md) is `[x]`.
---
 
## Coverage Dashboard
 
Live counters. Update alongside any test add/remove.
 
### Totals
 
| Metric | Count |
|---|---|
| **Total test cases** | **59** |
| Passing (`[x]`) | 0 |
| Outstanding (`[ ]`) | 59 |
| Pass rate | 0% |
 
### By severity
 
| Severity | Count | Passing | Outstanding |
|---|---|---|---|
| P0 — demo blockers | 30 | 0 | 30 |
| P1 — demo degraders | 27 | 0 | 27 |
| P2 — polish | 2 | 0 | 2 |
 
### By type
 
| Type | Count |
|---|---|
| Unit | 13 |
| Integration | 18 |
| Manual | 13 |
| Boundary | 15 |
 
### By suite
 
| Suite | Section | Count |
|---|---|---|
| Pipeline extraction | [§1](#1-pipeline-extraction-tests) | 14 |
| Vector search & fusion | [§2](#2-vector-search--fusion-tests) | 13 |
| Graph lineage | [§3](#3-graph-lineage-validation) | 5 |
| Live UI integration | [§4](#4-live-ui-integration-tests) | 12 |
| Discipline & quality gates | [§5](#5-discipline--code-quality-gates) | 6 |
| Failure boundaries | [§6](#6-failure-boundary-assertions) | 9 |
 
### Task coverage
 
Verifies that every actionable task in [TASKS.md](TASKS.md) is guarded by at least one test case. See full mapping in [§7 Traceability Matrix](#7-traceability-matrix).
 
| Metric | Value |
|---|---|
| Testable tasks in TASKS.md | 39 |
| Tasks with ≥ 1 test | 39 |
| **Task coverage** | **100%** |
| Tasks intentionally untested | 1 (T-3.4.2 — README badges, cosmetic) |
 
### Gate to demo-ready
 
Demo can be performed when:
 
- 100% of P0 cases (30/30) are `[x]`.
- ≥ 80% of P1 cases (≥ 22/27) are `[x]`.
- All `TC-DEMO-*` cases (5 total) are `[x]`.
---
 
## 1. Pipeline Extraction Tests
 
Validates crawl, OCR, and Mistral structured decode. **Suite total: 14** (P0: 6 · P1: 8 · P2: 0).
 
- [ ] **TC-ENV-001** · P0 · Manual — Fresh-box install on macOS + Ubuntu.
  - Asserts: all five binaries (`tesseract`, `qdrant`, `cypher-shell`, `python3.11`, `node`) exit 0 on `--version`.
  - Tracks: [T-1.1.1](TASKS.md#feature-f-11--local-infrastructure-bootstrap), [T-1.1.2](TASKS.md#feature-f-11--local-infrastructure-bootstrap).
- [ ] **TC-ENV-002** · P0 · Unit — Missing required env var.
  - Asserts: `from backend import config` raises with all missing keys named in one message; partial boot is impossible.
  - Tracks: [T-1.1.3](TASKS.md#feature-f-11--local-infrastructure-bootstrap).
- [ ] **TC-CRAWL-001** · P0 · Integration — Top-100 dry run on `r/memes`.
  - Asserts: `data/memes.json` length ≥ 90 (allowing for NSFW/self filtering); every record carries `id`, `image_path`, `post_title`, `upvotes`.
  - Tracks: [T-1.2.1](TASKS.md#feature-f-12--reddit-crawler).
- [ ] **TC-CRAWL-002** · P1 · Boundary — Crawler interrupted at post #37, resumed.
  - Asserts: after resume, the checkpoint contains all 37 prior records + new ones. No duplicates by Reddit `id`.
  - Tracks: [T-1.2.1](TASKS.md#feature-f-12--reddit-crawler).
- [ ] **TC-CRAWL-003** · P1 · Unit — URL resolver.
  - Asserts: i.redd.it direct, imgur direct, and Reddit-preview-only posts all resolve to a downloadable URL with valid extension.
  - Tracks: [T-1.2.2](TASKS.md#feature-f-12--reddit-crawler).
- [ ] **TC-CRAWL-004** · P1 · Unit — Filter discipline.
  - Asserts: NSFW posts, text-only self-posts, and link-to-video posts are excluded from the manifest.
  - Tracks: [T-1.2.3](TASKS.md#feature-f-12--reddit-crawler).
- [ ] **TC-OCR-001** · P1 · Integration — OCR on classic top-text/bottom-text meme.
  - Asserts: returned text contains ≥ 80% of the ground-truth caption tokens.
  - Tracks: [T-1.3.3](TASKS.md#feature-f-13--mistral-structured-decoder).
- [ ] **TC-OCR-002** · P1 · Boundary — OCR on image with no text (cat photo).
  - Asserts: returns empty string, does not throw. Downstream decoder still produces valid JSON.
  - Tracks: [T-1.3.3](TASKS.md#feature-f-13--mistral-structured-decoder).
- [ ] **TC-LLM-001** · P0 · Integration — Decoder happy path.
  - Asserts: returned object parses cleanly into `MemeDecodeSchema`; `core_joke` ≤ 400 chars; `psychological_state` ≤ 120 chars. Spec: [CLAUDE.md §2.1](CLAUDE.md#21-mistral-decoder-output-schema).
  - Tracks: [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder).
- [ ] **TC-LLM-002** · P1 · Integration — Psychological state coverage.
  - Asserts: over 50 sample memes, at least 8 distinct values appear in `psychological_state` (no single-value collapse).
  - Tracks: [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder).
- [ ] **TC-LLM-003** · P1 · Integration — Subtext context coverage.
  - Asserts: same 50 samples, at least 10 distinct values in `subtext_context`.
  - Tracks: [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder).
- [ ] **TC-LLM-004** · P0 · Unit — Dense-explanations length floor.
  - Asserts: `search_dense_explanations` ≥ 40 chars on every successful decode.
  - Tracks: [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder).
- [ ] **TC-LLM-005** · P1 · Boundary — Malformed JSON recovery.
  - Asserts: inject a markdown-fenced response — `_coerce_json` recovers. Inject a non-JSON paragraph — `DecodeError` raised and meme logged to a quarantine list, not retried inline.
  - Tracks: [T-1.3.2](TASKS.md#feature-f-13--mistral-structured-decoder).
- [ ] **TC-ING-005** · P0 · Manual — `--limit 50` smoke ingest.
  - Asserts: after run, Qdrant point count = 50; Neo4j Meme node count = 50; failures table empty or all explicable.
  - Tracks: [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert).
---
 
## 2. Vector Search & Fusion Tests
 
Validates Qdrant schema, embedding pipeline, RRF correctness, and weighting behavior. **Suite total: 13** (P0: 10 · P1: 3 · P2: 0).
 
- [ ] **TC-VEC-001** · P0 · Integration — Collection schema.
  - Asserts: `qdrant_client.get_collection("memeradar").config.params.vectors` contains exactly two named vectors, `visual` and `irony`, both size 1024, distance COSINE. Spec: [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping).
  - Tracks: [T-1.4.1](TASKS.md#feature-f-14--vector--graph-upsert).
- [ ] **TC-VEC-002** · P0 · Integration — Idempotency.
  - Asserts: re-run `python -m backend.ingest` on the same `memes.json` twice — point count unchanged.
  - Tracks: [T-1.4.2](TASKS.md#feature-f-14--vector--graph-upsert).
- [ ] **TC-VEC-003** · P1 · Unit — Spherical-mean centroid is unit length.
  - Asserts: `backend.mutation.spherical_mean(cluster)` on a realistic sample cluster returns a vector with `L2 == 1.0` (within `1e-9`); each pass (per-vector normalize → arithmetic mean → renormalize) is applied. Spec: [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping).
  - Note: this is the KSP 1 centroid assertion the spec requested as "TC-VEC-002"; that ID was already taken by Idempotency, so it lands here as TC-VEC-003 — see [implementation-notes.md](implementation-notes.md).
  - Tracks: [T-5.1.1](TASKS.md#feature-f-51--meme-mutation-radar-implementation), [T-5.1.3](TASKS.md#feature-f-51--meme-mutation-radar-implementation).
- [ ] **TC-RRF-001** · P0 · Unit — Visual text query.
  - Asserts: `tl_text_embedding("panic")` returns 1024 floats in `[-1, 1]`.
  - Tracks: [T-2.2.1](TASKS.md#feature-f-22--dual-query-embedding).
- [ ] **TC-RRF-002** · P0 · Unit — Irony text query.
  - Asserts: `mistral_embed("panic")` returns 1024 floats in `[-1, 1]`.
  - Tracks: [T-2.2.2](TASKS.md#feature-f-22--dual-query-embedding).
- [ ] **TC-RRF-003** · P0 · Integration — Single-space fallback.
  - Asserts: with `visual_weight=1.0, irony_weight=0.0`, the irony prefetch limit collapses to floor (5). Result set differs from balanced query in ≥ 60% of top-10 IDs.
  - Tracks: [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api).
- [ ] **TC-RRF-004** · P0 · Integration — Universal Query API shape.
  - Asserts: the HTTP request to Qdrant contains exactly two `prefetch` entries and a `query: {fusion: "rrf"}` block. Captured via SDK trace.
  - Tracks: [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api).
- [ ] **TC-RRF-005** · P1 · Unit — Weight to candidate function.
  - Asserts: `_candidates_per_space(weight=0.0, k=20)` ≥ floor of 5; `weight=1.0, k=20` returns 80; monotonic in between.
  - Tracks: [T-2.3.2](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api).
- [ ] **TC-RRF-006** · P1 · Unit — Weight normalization.
  - Asserts: `Weights(visual=2, irony=2).normalized()` → `(0.5, 0.5)`. `Weights(0, 0).normalized()` → `(0.5, 0.5)`.
  - Tracks: [T-2.3.2](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api).
- [ ] **TC-RRF-007** · P0 · Boundary — Zero-result query.
  - Asserts: `GET /search?q=zzzzzzz_unmatched_token_xyz_123` returns HTTP 200, `count: 0`, `results: []`. Never 404, never 500. Spec: [CLAUDE.md §2.3 invariant 4](CLAUDE.md#23-fastapi-search-schema).
  - Tracks: [T-2.3.3](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api).
- [ ] **TC-DEMO-001** · P0 · Integration — Rank shift across sweep.
  - Asserts: `scripts/rrf_sweep.py` reports `top1(A=1.0/0.0) ≠ top1(E=0.0/1.0)`. Spec: [README.md §4.3 assertion 1](README.md#43-rrf-validation-assertions).
  - Tracks: [T-2.5.1](TASKS.md#feature-f-25--rrf-rank-shift-validator).
- [ ] **TC-DEMO-002** · P0 · Integration — Monotonic Jaccard.
  - Asserts: across A→E sweep, `J(A,B) > J(A,C) > J(A,D) > J(A,E)`. Spec: [README.md §4.3 assertion 2](README.md#43-rrf-validation-assertions).
  - Tracks: [T-2.5.1](TASKS.md#feature-f-25--rrf-rank-shift-validator).
- [ ] **TC-DEMO-003** · P0 · Integration — CI exit code contract.
  - Asserts: inject a synthetic dataset that violates monotonicity — `rrf_sweep.py` exits ≠ 0. Restore — exits 0. Spec: [README.md §4.4](README.md#44-validation-script-hook).
  - Tracks: [T-2.5.2](TASKS.md#feature-f-25--rrf-rank-shift-validator).
---
 
## 3. Graph Lineage Validation
 
Validates Neo4j MERGE discipline, Cognee enrichment, and lineage retrieval. **Suite total: 5** (P0: 2 · P1: 3 · P2: 0).
 
- [ ] **TC-GRAPH-001** · P0 · Integration — Template merge.
  - Asserts: after ingesting 1000 memes, every `Meme` node has exactly one outgoing `:USES_TEMPLATE` edge.
  - Tracks: [T-1.4.3](TASKS.md#feature-f-14--vector--graph-upsert).
- [ ] **TC-GRAPH-002** · P1 · Integration — Lineage payload.
  - Asserts: `/search` response — ≥ 80% of `MemeHit.lineage.template` are non-null after Cognee enrichment. Spec: [CLAUDE.md §2.3 MemeHit.lineage](CLAUDE.md#23-fastapi-search-schema).
  - Tracks: [T-2.4.1](TASKS.md#feature-f-24--lineage-join), [T-1.5.1](TASKS.md#feature-f-15--knowledge-graph-enrichment).
- [ ] **TC-GRAPH-003** · P0 · Boundary — Re-ingest does not duplicate.
  - Asserts: running ingest twice — count of `:USES_TEMPLATE` edges unchanged. Spec: [CLAUDE.md §3.3](CLAUDE.md#33-determinism--idempotency).
  - Tracks: [T-1.4.3](TASKS.md#feature-f-14--vector--graph-upsert).
- [ ] **TC-GRAPH-004** · P1 · Integration — Cognee enrichment.
  - Asserts: after `enrich_cognee.py`, at least 5 `:VARIATION_OF` edges exist between distinct templates.
  - Tracks: [T-1.5.1](TASKS.md#feature-f-15--knowledge-graph-enrichment).
- [ ] **TC-GRAPH-005** · P1 · Unit — Lineage Cypher recursion.
  - Asserts: query with `*0..2` returns the template itself + up to 2 hops of variants; never returns the seed meme as a variant.
  - Tracks: [T-2.4.1](TASKS.md#feature-f-24--lineage-join).
---
 
## 4. Live UI Integration Tests
 
Validates the React surface end-to-end against a running FastAPI. **Suite total: 12** (P0: 6 · P1: 6 · P2: 0).
 
- [ ] **TC-API-001** · P0 · Integration — Search response schema.
  - Asserts: `GET /search?q=panic` body deserializes into `SearchResponse` per [CLAUDE.md §2.3](CLAUDE.md#23-fastapi-search-schema); invariant `len(results) == count` holds.
  - Tracks: [T-2.1.1](TASKS.md#feature-f-21--pydantic-contracts).
- [ ] **TC-API-002** · P1 · Boundary — Weight validation.
  - Asserts: `GET /search?q=x&visual_weight=0&irony_weight=0` returns HTTP 422, not silent default.
  - Tracks: [T-2.1.2](TASKS.md#feature-f-21--pydantic-contracts).
- [ ] **TC-UI-001** · P0 · Manual — Cold-start search.
  - Asserts: fresh page load, type query, hit enter — grid renders within 3s with ≥ 1 result.
  - Tracks: [T-3.1.1](TASKS.md#feature-f-31--react-shell), [T-3.1.2](TASKS.md#feature-f-31--react-shell).
- [ ] **TC-UI-002** · P1 · Manual — Grid responsiveness.
  - Asserts: at 1440px viewport, 6+ columns; at 768px, 3+ columns; at 380px, 1+ column. No image clipping.
  - Tracks: [T-3.1.2](TASKS.md#feature-f-31--react-shell).
- [ ] **TC-UI-003** · P0 · Manual — Live slider rebinding.
  - Asserts: slider drag from 0.0 to 1.0 triggers refetch (debounced ≤ 300ms); top-1 tile visibly changes.
  - Tracks: [T-3.2.1](TASKS.md#feature-f-32--weight-slider--rrf-visibility).
- [ ] **TC-UI-004** · P0 · Manual — Detail modal.
  - Asserts: click any result — modal shows `core_joke`, `psychological_state`, `subtext_context`, and lineage block. Esc closes.
  - Tracks: [T-3.2.2](TASKS.md#feature-f-32--weight-slider--rrf-visibility).
- [ ] **TC-UI-005** · P1 · Manual — Empty state.
  - Asserts: type a deliberately unmatched query — UI shows "no memes match", not a broken grid.
  - Tracks: [T-3.3.1](TASKS.md#feature-f-33--failure-surfaces).
- [ ] **TC-UI-006** · P1 · Manual — Backend down.
  - Asserts: stop FastAPI mid-session; next search shows a toast "search service unavailable"; previous grid stays visible.
  - Tracks: [T-3.3.2](TASKS.md#feature-f-33--failure-surfaces).
- [ ] **TC-UI-007** · P1 · Manual — Small-sample "accumulating baseline" banner.
  - Asserts: open the Meme Mutation Radar panel for a meme whose template has `< MUTATION_MIN_MEMBERS` (5) members; the panel replaces the live velocity graph with the banner "Accumulating baseline data: This template requires at least 5 instances for drift telemetry." No velocity bar is shown.
  - Note: this is the KSP 1 UI case the spec requested as "TC-UI-001"; that ID was already taken by Cold-start search, so it lands here as TC-UI-007 — see [implementation-notes-ui.html](implementation-notes-ui.html) (mirrors the TC-VEC / TC-FAIL renames in [implementation-notes.md](implementation-notes.md)).
  - Tracks: [T-5.2.3](TASKS.md#feature-f-52--meme-mutation-radar-dashboard-panel-frontend), [T-5.2.4](TASKS.md#feature-f-52--meme-mutation-radar-dashboard-panel-frontend).
- [ ] **TC-UI-008** · P1 · Manual — Trend Velocity badge state.
  - Asserts: when the selected meme's template carries `trending_mutation == true`, the badge reads "Trending Mutation" (High Velocity) with the flame/graph treatment; when `false`, it reads "Stable Format". Driven by the mapped `trending_mutation` payload property.
  - Note: this is the KSP 1 UI case the spec requested as "TC-UI-002"; that ID was already taken by Grid responsiveness, so it lands here as TC-UI-008 — see [implementation-notes-ui.html](implementation-notes-ui.html).
  - Tracks: [T-5.2.1](TASKS.md#feature-f-52--meme-mutation-radar-dashboard-panel-frontend), [T-5.2.2](TASKS.md#feature-f-52--meme-mutation-radar-dashboard-panel-frontend).
- [ ] **TC-DEMO-004** · P0 · Manual — RRF sweep visually.
  - Asserts: operator performs the 5-step sweep from [README.md §4.2](README.md#42-manual-rrf-sweep-procedure); top-1 shifts and at least 3 distinct memes appear as top-1 across the 5 steps.
  - Tracks: [T-3.2.1](TASKS.md#feature-f-32--weight-slider--rrf-visibility).
- [ ] **TC-DEMO-005** · P0 · Manual — 3-minute demo dry run.
  - Asserts: run the full demo script end-to-end with a stopwatch; finish under 180s; no crashes; mic capture intact.
  - Tracks: [T-3.4.1](TASKS.md#feature-f-34--demo-capture).
---
 
## 5. Discipline & Code Quality Gates
 
Enforces the engineering rules from [CLAUDE.md §3](CLAUDE.md#3-system-rules--engineering-constraints). **Suite total: 6** (P0: 3 · P1: 3 · P2: 0).
 
- [ ] **TC-DISC-001** · P0 · Unit — No comments / docstrings in app code.
  - Asserts: linter scans `backend/**/*.py` (except `schemas.py`) and `scripts/**/*.py`; fails on any `#`-line comment, inline comment, or triple-quoted docstring. Spec: [CLAUDE.md §3.1](CLAUDE.md#31-comment--docstring-prohibition-application-code).
  - Tracks: [T-X.1](TASKS.md#cross-cutting-spans-all-sprints).
- [ ] **TC-DISC-002** · P0 · Unit — Async loop audit.
  - Asserts: static check — every public function in `backend/main.py`, `backend/search.py`, `backend/ingest.py` is `async def`; every Twelve Labs / Mistral / Qdrant / Neo4j call site is either awaited or wrapped in `asyncio.to_thread`. Spec: [CLAUDE.md §3.2](CLAUDE.md#32-async-processing-loops).
  - Tracks: [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert).
- [ ] **TC-DISC-003** · P0 · Unit — Vendor containment.
  - Asserts: audit script greps for vendor SDK imports — fails if any forbidden import appears outside its owning module per [CLAUDE.md §3.6](CLAUDE.md#36-vendor-boundaries).
  - Tracks: [T-X.2](TASKS.md#cross-cutting-spans-all-sprints).
- [ ] **TC-DISC-004** · P1 · Manual — No Docker.
  - Asserts: `find . -iname 'Dockerfile' -o -iname 'docker-compose*'` returns empty. Spec: [CLAUDE.md §3.5](CLAUDE.md#35-no-docker).
  - Tracks: [T-1.1.1](TASKS.md#feature-f-11--local-infrastructure-bootstrap).
- [ ] **TC-PERF-001** · P1 · Integration — Ingest throughput.
  - Asserts: 1000 memes ingest under 45 minutes on a 4-core laptop with 4 async workers; mean per-meme < 3s end-to-end.
  - Tracks: [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert).
- [ ] **TC-PERF-002** · P1 · Integration — Search latency.
  - Asserts: p50 of `/search?q=...&k=20` under 800ms warm cache; p95 under 1800ms.
  - Tracks: [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api).
---
 
## 6. Failure Boundary Assertions
 
Edge-case behavior that protects the demo from disaster. **Suite total: 9** (P0: 3 · P1: 4 · P2: 2).
 
- [ ] **TC-FAIL-001** · P0 · Boundary — Dead Twelve Labs key.
  - Asserts: invalid `TL_API_KEY` at ingest time — affected memes land in a quarantine list; pipeline continues for the rest; no Qdrant point upserted with empty `visual` vector.
  - Tracks: [T-1.3.2](TASKS.md#feature-f-13--mistral-structured-decoder), [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert).
- [ ] **TC-FAIL-002** · P0 · Boundary — Dead Mistral key.
  - Asserts: invalid `MISTRAL_API_KEY` at ingest time — decoder raises `DecodeError`; ingestion task records the failure with Reddit `id`; pipeline does not crash. Spec: [CLAUDE.md §2.1 failure-mode contract](CLAUDE.md#21-mistral-decoder-output-schema).
  - Tracks: [T-1.3.2](TASKS.md#feature-f-13--mistral-structured-decoder).
- [ ] **TC-FAIL-003** · P0 · Boundary — Zero-result multi-vector.
  - Asserts: query that exists in irony space but with `visual_weight=1.0, irony_weight=0.0` and no matching visual neighbors — endpoint returns `count: 0, results: []`. Spec: [CLAUDE.md §2.3 invariant 4](CLAUDE.md#23-fastapi-search-schema).
  - Tracks: [T-2.3.3](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api), [T-3.3.1](TASKS.md#feature-f-33--failure-surfaces).
- [ ] **TC-FAIL-004** · P1 · Boundary — OCR returns garbage.
  - Asserts: OCR yields 200 chars of noise on a screenshot meme; Mistral decoder still produces a valid `MemeDecodeSchema` by leaning on the post title alone.
  - Tracks: [T-1.3.3](TASKS.md#feature-f-13--mistral-structured-decoder).
- [ ] **TC-FAIL-005** · P1 · Boundary — Neo4j unavailable mid-search.
  - Asserts: stop Neo4j; `/search` still returns the RRF-ranked memes but with `lineage.template = null, lineage.variants = []`. Never 500.
  - Tracks: [T-2.4.1](TASKS.md#feature-f-24--lineage-join).
- [ ] **TC-FAIL-006** · P1 · Boundary — Qdrant unavailable.
  - Asserts: stop Qdrant; `/search` returns HTTP 503 with a structured error body; FastAPI does not leak stack trace.
  - Tracks: [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api).
- [ ] **TC-FAIL-007** · P2 · Boundary — Oversized query.
  - Asserts: `q` of 401 characters — HTTP 422 with `SearchQueryParams` validation error. Spec: [CLAUDE.md §2.3](CLAUDE.md#23-fastapi-search-schema).
  - Tracks: [T-2.1.1](TASKS.md#feature-f-21--pydantic-contracts).
- [ ] **TC-FAIL-008** · P2 · Boundary — Image disappears between crawl and ingest.
  - Asserts: manually delete one image file; ingest task for that meme is quarantined; the rest proceed.
  - Tracks: [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert).
- [ ] **TC-FAIL-009** · P1 · Boundary — Small-sample mutation guardrail.
  - Asserts: a template with `< 5` members run through `scripts/compute_mutation_metrics.py` defaults `velocity` to `0.0` and forces `trending_mutation = false` without raising; the template is flagged "accumulating baseline data" and velocity computation is bypassed. Spec: [implementation-notes.md](implementation-notes.md).
  - Note: this is the KSP 1 guardrail the spec requested as "TC-FAIL-007"; that ID was already taken by Oversized query, so it lands here as TC-FAIL-009 — see [implementation-notes.md](implementation-notes.md).
  - Tracks: [T-5.1.4](TASKS.md#feature-f-51--meme-mutation-radar-implementation).
---
 
## 7. Traceability Matrix
 
Reverse index — every task in [TASKS.md](TASKS.md) and its guarding tests.
 
| Task | Required tests | Count |
|---|---|---|
| [T-1.1.1](TASKS.md#feature-f-11--local-infrastructure-bootstrap) | TC-ENV-001, TC-DISC-004 | 2 |
| [T-1.1.2](TASKS.md#feature-f-11--local-infrastructure-bootstrap) | TC-ENV-001 | 1 |
| [T-1.1.3](TASKS.md#feature-f-11--local-infrastructure-bootstrap) | TC-ENV-002 | 1 |
| [T-1.2.1](TASKS.md#feature-f-12--reddit-crawler) | TC-CRAWL-001, TC-CRAWL-002 | 2 |
| [T-1.2.2](TASKS.md#feature-f-12--reddit-crawler) | TC-CRAWL-003 | 1 |
| [T-1.2.3](TASKS.md#feature-f-12--reddit-crawler) | TC-CRAWL-004 | 1 |
| [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder) | TC-LLM-001, TC-LLM-002, TC-LLM-003, TC-LLM-004 | 4 |
| [T-1.3.2](TASKS.md#feature-f-13--mistral-structured-decoder) | TC-LLM-005, TC-FAIL-001, TC-FAIL-002 | 3 |
| [T-1.3.3](TASKS.md#feature-f-13--mistral-structured-decoder) | TC-OCR-001, TC-OCR-002, TC-FAIL-004 | 3 |
| [T-1.4.1](TASKS.md#feature-f-14--vector--graph-upsert) | TC-VEC-001 | 1 |
| [T-1.4.2](TASKS.md#feature-f-14--vector--graph-upsert) | TC-VEC-002 | 1 |
| [T-1.4.3](TASKS.md#feature-f-14--vector--graph-upsert) | TC-GRAPH-001, TC-GRAPH-003 | 2 |
| [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert) | TC-ING-005, TC-DISC-002, TC-PERF-001, TC-FAIL-001, TC-FAIL-008 | 5 |
| [T-1.5.1](TASKS.md#feature-f-15--knowledge-graph-enrichment) | TC-GRAPH-002, TC-GRAPH-004 | 2 |
| [T-2.1.1](TASKS.md#feature-f-21--pydantic-contracts) | TC-API-001, TC-FAIL-007 | 2 |
| [T-2.1.2](TASKS.md#feature-f-21--pydantic-contracts) | TC-API-002 | 1 |
| [T-2.2.1](TASKS.md#feature-f-22--dual-query-embedding) | TC-RRF-001 | 1 |
| [T-2.2.2](TASKS.md#feature-f-22--dual-query-embedding) | TC-RRF-002 | 1 |
| [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) | TC-RRF-003, TC-RRF-004, TC-PERF-002, TC-FAIL-006 | 4 |
| [T-2.3.2](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) | TC-RRF-005, TC-RRF-006 | 2 |
| [T-2.3.3](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) | TC-RRF-007, TC-FAIL-003 | 2 |
| [T-2.4.1](TASKS.md#feature-f-24--lineage-join) | TC-GRAPH-002, TC-GRAPH-005, TC-FAIL-005 | 3 |
| [T-2.5.1](TASKS.md#feature-f-25--rrf-rank-shift-validator) | TC-DEMO-001, TC-DEMO-002 | 2 |
| [T-2.5.2](TASKS.md#feature-f-25--rrf-rank-shift-validator) | TC-DEMO-003 | 1 |
| [T-3.1.1](TASKS.md#feature-f-31--react-shell) | TC-UI-001 | 1 |
| [T-3.1.2](TASKS.md#feature-f-31--react-shell) | TC-UI-001, TC-UI-002 | 2 |
| [T-3.2.1](TASKS.md#feature-f-32--weight-slider--rrf-visibility) | TC-UI-003, TC-DEMO-004 | 2 |
| [T-3.2.2](TASKS.md#feature-f-32--weight-slider--rrf-visibility) | TC-UI-004 | 1 |
| [T-3.3.1](TASKS.md#feature-f-33--failure-surfaces) | TC-UI-005, TC-FAIL-003 | 2 |
| [T-3.3.2](TASKS.md#feature-f-33--failure-surfaces) | TC-UI-006 | 1 |
| [T-3.4.1](TASKS.md#feature-f-34--demo-capture) | TC-DEMO-005 | 1 |
| [T-3.4.2](TASKS.md#feature-f-34--demo-capture) | — (cosmetic, no test required) | 0 |
| [T-5.1.1](TASKS.md#feature-f-51--meme-mutation-radar-implementation) | TC-VEC-003 | 1 |
| [T-5.1.2](TASKS.md#feature-f-51--meme-mutation-radar-implementation) | TC-VEC-003, TC-FAIL-009 | 2 |
| [T-5.1.3](TASKS.md#feature-f-51--meme-mutation-radar-implementation) | TC-VEC-003 | 1 |
| [T-5.1.4](TASKS.md#feature-f-51--meme-mutation-radar-implementation) | TC-FAIL-009 | 1 |
| [T-5.2.1](TASKS.md#feature-f-52--meme-mutation-radar-dashboard-panel-frontend) | TC-UI-008 | 1 |
| [T-5.2.2](TASKS.md#feature-f-52--meme-mutation-radar-dashboard-panel-frontend) | TC-UI-008 | 1 |
| [T-5.2.3](TASKS.md#feature-f-52--meme-mutation-radar-dashboard-panel-frontend) | TC-UI-007 | 1 |
| [T-5.2.4](TASKS.md#feature-f-52--meme-mutation-radar-dashboard-panel-frontend) | TC-UI-007, TC-UI-008 | 2 |
| [T-X.1](TASKS.md#cross-cutting-spans-all-sprints) | TC-DISC-001 | 1 |
| [T-X.2](TASKS.md#cross-cutting-spans-all-sprints) | TC-DISC-003 | 1 |
 