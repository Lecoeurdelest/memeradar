# TESTS.md — Traceability QA Matrix

> End-to-end test playbook. Every case maps back to a task in [TASKS.md](TASKS.md) and a spec in [CLAUDE.md](CLAUDE.md).
>
> Companion documents: [README.md](README.md) · [CLAUDE.md](CLAUDE.md) · [TASKS.md](TASKS.md)

---

## Conventions

- ID prefix indicates suite: `ENV`, `CRAWL`, `OCR`, `LLM`, `VEC`, `RRF`, `GRAPH`, `API`, `UI`, `DEMO`, `DISC`, `PERF`, `FAIL`.
- `Severity`: P0 (blocks demo), P1 (degrades demo), P2 (quality polish).
- `Type`: Unit | Integration | Manual | Boundary.
- A test passes only when its `Asserts` column holds AND its linked task in [TASKS.md](TASKS.md) is marked `[x]`.

---

## 1. Pipeline Extraction Tests

Validates crawl, OCR, and Mistral structured decode.

| ID | Severity | Type | Description | Asserts | Tracks task |
|---|---|---|---|---|---|
| **TC-ENV-001** | P0 | Manual | Fresh-box install on macOS + Ubuntu | All five binaries (`tesseract`, `qdrant`, `cypher-shell`, `python3.11`, `node`) exit 0 on `--version`. | [T-1.1.1](TASKS.md#feature-f-11--local-infrastructure-bootstrap), [T-1.1.2](TASKS.md#feature-f-11--local-infrastructure-bootstrap) |
| **TC-ENV-002** | P0 | Unit | Missing required env var | `from backend import config` raises with all missing keys named in one message; partial boot is impossible. | [T-1.1.3](TASKS.md#feature-f-11--local-infrastructure-bootstrap) |
| **TC-CRAWL-001** | P0 | Integration | Top-100 dry run on `r/memes` | `data/memes.json` length ≥ 90 (allowing for NSFW/self filtering); every record carries `id`, `image_path`, `post_title`, `upvotes`. | [T-1.2.1](TASKS.md#feature-f-12--reddit-crawler) |
| **TC-CRAWL-002** | P1 | Boundary | Crawler interrupted at post #37, resumed | After resume, the checkpoint contains all 37 prior records + new ones. No duplicates by Reddit `id`. | [T-1.2.1](TASKS.md#feature-f-12--reddit-crawler) |
| **TC-CRAWL-003** | P1 | Unit | URL resolver | i.redd.it direct, imgur direct, and Reddit-preview-only posts all resolve to a downloadable URL with valid extension. | [T-1.2.2](TASKS.md#feature-f-12--reddit-crawler) |
| **TC-CRAWL-004** | P1 | Unit | Filter discipline | NSFW posts, text-only self-posts, and link-to-video posts are excluded from the manifest. | [T-1.2.3](TASKS.md#feature-f-12--reddit-crawler) |
| **TC-OCR-001** | P1 | Integration | OCR on classic top-text/bottom-text meme | Returned text contains ≥ 80% of the ground-truth caption tokens. | [T-1.3.3](TASKS.md#feature-f-13--mistral-structured-decoder) |
| **TC-OCR-002** | P1 | Boundary | OCR on image with no text (cat photo) | Returns empty string, does not throw. Downstream decoder still produces valid JSON. | [T-1.3.3](TASKS.md#feature-f-13--mistral-structured-decoder) |
| **TC-LLM-001** | P0 | Integration | Decoder happy path | Returned object parses cleanly into `MemeDecodeSchema`; `core_joke` ≤ 400 chars; `psychological_state` ≤ 120 chars. Spec: [CLAUDE.md §2.1](CLAUDE.md#21-mistral-decoder-output-schema). | [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder) |
| **TC-LLM-002** | P1 | Integration | Psychological state coverage | Over 50 sample memes, at least 8 distinct values appear in `psychological_state` (no single-value collapse). | [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder) |
| **TC-LLM-003** | P1 | Integration | Subtext context coverage | Same 50 samples: at least 10 distinct values in `subtext_context`. | [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder) |
| **TC-LLM-004** | P0 | Unit | Dense-explanations length floor | `search_dense_explanations` ≥ 40 chars on every successful decode. | [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder) |
| **TC-LLM-005** | P1 | Boundary | Malformed JSON recovery | Inject a markdown-fenced response — `_coerce_json` recovers; inject a non-JSON paragraph — `DecodeError` raised and meme is logged to a quarantine list, not retried inline. | [T-1.3.2](TASKS.md#feature-f-13--mistral-structured-decoder) |
| **TC-ING-005** | P0 | Manual | `--limit 50` smoke ingest | After run: Qdrant point count = 50; Neo4j Meme node count = 50; failures table is empty or all explicable. | [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert) |

---

## 2. Vector Search & Fusion Tests

Validates Qdrant schema, embedding pipeline, RRF correctness, and weighting behavior.

| ID | Severity | Type | Description | Asserts | Tracks task |
|---|---|---|---|---|---|
| **TC-VEC-001** | P0 | Integration | Collection schema | `qdrant_client.get_collection("memeradar").config.params.vectors` contains exactly two named vectors, `visual` and `irony`, both size 1024, distance COSINE. Spec: [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping). | [T-1.4.1](TASKS.md#feature-f-14--vector--graph-upsert) |
| **TC-VEC-002** | P0 | Integration | Idempotency | Re-run `python -m backend.ingest` on the same `memes.json` twice — point count unchanged. | [T-1.4.2](TASKS.md#feature-f-14--vector--graph-upsert) |
| **TC-RRF-001** | P0 | Unit | Visual text query | `tl_text_embedding("panic")` returns 1024 floats in `[-1, 1]`. | [T-2.2.1](TASKS.md#feature-f-22--dual-query-embedding) |
| **TC-RRF-002** | P0 | Unit | Irony text query | `mistral_embed("panic")` returns 1024 floats in `[-1, 1]`. | [T-2.2.2](TASKS.md#feature-f-22--dual-query-embedding) |
| **TC-RRF-003** | P0 | Integration | Single-space fallback | With `visual_weight=1.0, irony_weight=0.0`, the irony prefetch limit collapses to floor (5). Result set differs from balanced query in ≥ 60% of top-10 IDs. | [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) |
| **TC-RRF-004** | P0 | Integration | Universal Query API shape | The HTTP request to Qdrant contains exactly two `prefetch` entries and a `query: {fusion: "rrf"}` block. Captured via SDK trace. | [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) |
| **TC-RRF-005** | P1 | Unit | Weight → candidate function | `_candidates_per_space(weight=0.0, k=20)` ≥ floor of 5; `weight=1.0, k=20` returns 80; monotonic in between. | [T-2.3.2](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) |
| **TC-RRF-006** | P1 | Unit | Weight normalization | `Weights(visual=2, irony=2).normalized()` → `(0.5, 0.5)`. `Weights(0, 0).normalized()` → `(0.5, 0.5)`. | [T-2.3.2](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) |
| **TC-RRF-007** | P0 | Boundary | Zero-result query | `GET /search?q=zzzzzzz_unmatched_token_xyz_123` returns HTTP 200, `count: 0`, `results: []`. Never 404, never 500. Spec: [CLAUDE.md §2.3 invariant 4](CLAUDE.md#23-fastapi-search-schema). | [T-2.3.3](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) |
| **TC-DEMO-001** | P0 | Integration | Rank shift across sweep | `scripts/rrf_sweep.py` reports `top1(A=1.0/0.0) ≠ top1(E=0.0/1.0)`. Spec: [README.md §4.3 assertion 1](README.md#43-rrf-validation-assertions). | [T-2.5.1](TASKS.md#feature-f-25--rrf-rank-shift-validator) |
| **TC-DEMO-002** | P0 | Integration | Monotonic Jaccard | Across A→E sweep: `J(A,B) > J(A,C) > J(A,D) > J(A,E)`. Spec: [README.md §4.3 assertion 2](README.md#43-rrf-validation-assertions). | [T-2.5.1](TASKS.md#feature-f-25--rrf-rank-shift-validator) |
| **TC-DEMO-003** | P0 | Integration | CI exit code contract | Inject a synthetic dataset that violates monotonicity — `rrf_sweep.py` exits ≠ 0. Restore — exits 0. Spec: [README.md §4.4](README.md#44-validation-script-hook). | [T-2.5.2](TASKS.md#feature-f-25--rrf-rank-shift-validator) |

---

## 3. Graph Lineage Validation

Validates Neo4j MERGE discipline, Cognee enrichment, and lineage retrieval.

| ID | Severity | Type | Description | Asserts | Tracks task |
|---|---|---|---|---|---|
| **TC-GRAPH-001** | P0 | Integration | Template merge | After ingesting 1000 memes, every `Meme` node has exactly one outgoing `:USES_TEMPLATE` edge. | [T-1.4.3](TASKS.md#feature-f-14--vector--graph-upsert) |
| **TC-GRAPH-002** | P1 | Integration | Lineage payload | `/search` response: ≥ 80% of `MemeHit.lineage.template` are non-null after Cognee enrichment. Spec: [CLAUDE.md §2.3 MemeHit.lineage](CLAUDE.md#23-fastapi-search-schema). | [T-2.4.1](TASKS.md#feature-f-24--lineage-join), [T-1.5.1](TASKS.md#feature-f-15--knowledge-graph-enrichment) |
| **TC-GRAPH-003** | P0 | Boundary | Re-ingest does not duplicate | Running ingest twice — count of `:USES_TEMPLATE` edges unchanged. Spec: [CLAUDE.md §3.3](CLAUDE.md#33-determinism--idempotency). | [T-1.4.3](TASKS.md#feature-f-14--vector--graph-upsert) |
| **TC-GRAPH-004** | P1 | Integration | Cognee enrichment | After `enrich_cognee.py`, at least 5 `:VARIATION_OF` edges exist between distinct templates. | [T-1.5.1](TASKS.md#feature-f-15--knowledge-graph-enrichment) |
| **TC-GRAPH-005** | P1 | Unit | Lineage Cypher recursion | Query with `*0..2` returns the template itself + up to 2 hops of variants; never returns the seed meme as a variant. | [T-2.4.1](TASKS.md#feature-f-24--lineage-join) |

---

## 4. Live UI Integration Tests

Validates the React surface end-to-end against a running FastAPI.

| ID | Severity | Type | Description | Asserts | Tracks task |
|---|---|---|---|---|---|
| **TC-API-001** | P0 | Integration | Search response schema | `GET /search?q=panic` body deserializes into `SearchResponse` per [CLAUDE.md §2.3](CLAUDE.md#23-fastapi-search-schema); invariant `len(results) == count` holds. | [T-2.1.1](TASKS.md#feature-f-21--pydantic-contracts) |
| **TC-API-002** | P1 | Boundary | Weight validation | `GET /search?q=x&visual_weight=0&irony_weight=0` returns HTTP 422, not silent default. | [T-2.1.2](TASKS.md#feature-f-21--pydantic-contracts) |
| **TC-UI-001** | P0 | Manual | Cold-start search | Fresh page load, type query, hit enter — grid renders within 3s with ≥ 1 result. | [T-3.1.1](TASKS.md#feature-f-31--react-shell), [T-3.1.2](TASKS.md#feature-f-31--react-shell) |
| **TC-UI-002** | P1 | Manual | Grid responsiveness | At 1440px viewport, 6+ columns; at 768px, 3+ columns; at 380px, 1+ column. No image clipping. | [T-3.1.2](TASKS.md#feature-f-31--react-shell) |
| **TC-UI-003** | P0 | Manual | Live slider rebinding | Slider drag from 0.0 to 1.0 triggers refetch (debounced ≤ 300ms); top-1 tile visibly changes. | [T-3.2.1](TASKS.md#feature-f-32--weight-slider--rrf-visibility) |
| **TC-UI-004** | P0 | Manual | Detail modal | Click any result — modal shows `core_joke`, `psychological_state`, `subtext_context`, and the lineage block. Esc closes. | [T-3.2.2](TASKS.md#feature-f-32--weight-slider--rrf-visibility) |
| **TC-UI-005** | P1 | Manual | Empty state | Type a deliberately unmatched query — UI shows "no memes match", not a broken grid. | [T-3.3.1](TASKS.md#feature-f-33--failure-surfaces) |
| **TC-UI-006** | P1 | Manual | Backend down | Stop FastAPI mid-session; next search shows a toast "search service unavailable"; previous grid stays visible. | [T-3.3.2](TASKS.md#feature-f-33--failure-surfaces) |
| **TC-DEMO-004** | P0 | Manual | RRF sweep visually | Operator performs the 5-step sweep from [README.md §4.2](README.md#42-manual-rrf-sweep-procedure); top-1 shifts and at least 3 distinct memes appear as top-1 across the 5 steps. | [T-3.2.1](TASKS.md#feature-f-32--weight-slider--rrf-visibility) |
| **TC-DEMO-005** | P0 | Manual | 3-minute demo dry run | Run the full demo script end-to-end with a stopwatch; finish under 180s; no crashes; mic capture intact. | [T-3.4.1](TASKS.md#feature-f-34--demo-capture) |

---

## 5. Discipline & Code Quality Gates

Enforces the engineering rules from [CLAUDE.md §3](CLAUDE.md#3-system-rules--engineering-constraints).

| ID | Severity | Type | Description | Asserts | Tracks task |
|---|---|---|---|---|---|
| **TC-DISC-001** | P0 | Unit | No comments / docstrings in app code | Linter scans `backend/**/*.py` (except `schemas.py`) and `scripts/**/*.py`; fails on any `#`-line comment, inline comment, or triple-quoted docstring. Spec: [CLAUDE.md §3.1](CLAUDE.md#31-comment--docstring-prohibition-application-code). | [T-X.1](TASKS.md#cross-cutting-spans-all-sprints) |
| **TC-DISC-002** | P0 | Unit | Async loop audit | Static check: every public function in `backend/main.py`, `backend/search.py`, `backend/ingest.py` is `async def`; every Twelve Labs / Mistral / Qdrant / Neo4j call site is either awaited or wrapped in `asyncio.to_thread`. Spec: [CLAUDE.md §3.2](CLAUDE.md#32-async-processing-loops). | [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert) |
| **TC-DISC-003** | P0 | Unit | Vendor containment | Audit script greps for vendor SDK imports — fails if any forbidden import appears outside its owning module per [CLAUDE.md §3.6](CLAUDE.md#36-vendor-boundaries). | [T-X.2](TASKS.md#cross-cutting-spans-all-sprints) |
| **TC-DISC-004** | P1 | Manual | No Docker | `find . -iname 'Dockerfile' -o -iname 'docker-compose*'` returns empty. Spec: [CLAUDE.md §3.5](CLAUDE.md#35-no-docker). | [T-1.1.1](TASKS.md#feature-f-11--local-infrastructure-bootstrap) |
| **TC-PERF-001** | P1 | Integration | Ingest throughput | 1000 memes ingest under 45 minutes on a 4-core laptop with 4 async workers; mean per-meme < 3s end-to-end. | [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert) |
| **TC-PERF-002** | P1 | Integration | Search latency | p50 of `/search?q=...&k=20` under 800ms warm cache; p95 under 1800ms. | [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) |

---

## 6. Failure Boundary Assertions

Edge-case behavior that protects the demo from disaster.

| ID | Severity | Type | Description | Asserts | Tracks task |
|---|---|---|---|---|---|
| **TC-FAIL-001** | P0 | Boundary | Dead Twelve Labs key | Invalid `TL_API_KEY` at ingest time — affected memes land in a quarantine list; pipeline continues for the rest; no Qdrant point upserted with empty `visual` vector. | [T-1.3.2](TASKS.md#feature-f-13--mistral-structured-decoder), [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert) |
| **TC-FAIL-002** | P0 | Boundary | Dead Mistral key | Invalid `MISTRAL_API_KEY` at ingest time — decoder raises `DecodeError`; ingestion task records the failure with the Reddit `id`; pipeline does not crash. Spec: [CLAUDE.md §2.1 failure-mode contract](CLAUDE.md#21-mistral-decoder-output-schema). | [T-1.3.2](TASKS.md#feature-f-13--mistral-structured-decoder) |
| **TC-FAIL-003** | P0 | Boundary | Zero-result multi-vector | Query that exists in irony space but with `visual_weight=1.0, irony_weight=0.0` and no matching visual neighbors — endpoint returns `count: 0, results: []`. Spec: [CLAUDE.md §2.3 invariant 4](CLAUDE.md#23-fastapi-search-schema). | [T-2.3.3](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) |
| **TC-FAIL-004** | P1 | Boundary | OCR returns garbage | OCR yields 200 chars of noise on a screenshot meme; Mistral decoder still produces a valid `MemeDecodeSchema` by leaning on the post title alone. | [T-1.3.3](TASKS.md#feature-f-13--mistral-structured-decoder) |
| **TC-FAIL-005** | P1 | Boundary | Neo4j unavailable mid-search | Stop Neo4j; `/search` still returns the RRF-ranked memes but with `lineage.template = null, lineage.variants = []`. Never 500. | [T-2.4.1](TASKS.md#feature-f-24--lineage-join) |
| **TC-FAIL-006** | P1 | Boundary | Qdrant unavailable | Stop Qdrant; `/search` returns HTTP 503 with a structured error body; FastAPI does not leak stack trace. | [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) |
| **TC-FAIL-007** | P2 | Boundary | Oversized query | `q` of 401 characters — HTTP 422 with `SearchQueryParams` validation error. Spec: [CLAUDE.md §2.3](CLAUDE.md#23-fastapi-search-schema). | [T-2.1.1](TASKS.md#feature-f-21--pydantic-contracts) |
| **TC-FAIL-008** | P2 | Boundary | Image disappears between crawl and ingest | Manually delete one image file; ingest task for that meme is quarantined; the rest proceed. | [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert) |

---

## Traceability Summary

Per task, the set of tests gating its `[x]` status:

| Task | Required tests |
|---|---|
| [T-1.1.1 / T-1.1.2](TASKS.md#feature-f-11--local-infrastructure-bootstrap) | TC-ENV-001, TC-DISC-004 |
| [T-1.1.3](TASKS.md#feature-f-11--local-infrastructure-bootstrap) | TC-ENV-002 |
| [T-1.2.x](TASKS.md#feature-f-12--reddit-crawler) | TC-CRAWL-001..004 |
| [T-1.3.1](TASKS.md#feature-f-13--mistral-structured-decoder) | TC-LLM-001..004 |
| [T-1.3.2](TASKS.md#feature-f-13--mistral-structured-decoder) | TC-LLM-005, TC-FAIL-001, TC-FAIL-002 |
| [T-1.3.3](TASKS.md#feature-f-13--mistral-structured-decoder) | TC-OCR-001, TC-OCR-002, TC-FAIL-004 |
| [T-1.4.1](TASKS.md#feature-f-14--vector--graph-upsert) | TC-VEC-001 |
| [T-1.4.2](TASKS.md#feature-f-14--vector--graph-upsert) | TC-VEC-002 |
| [T-1.4.3](TASKS.md#feature-f-14--vector--graph-upsert) | TC-GRAPH-001, TC-GRAPH-003 |
| [T-1.4.4](TASKS.md#feature-f-14--vector--graph-upsert) | TC-ING-005, TC-DISC-002, TC-PERF-001, TC-FAIL-001, TC-FAIL-008 |
| [T-1.5.1](TASKS.md#feature-f-15--knowledge-graph-enrichment) | TC-GRAPH-002, TC-GRAPH-004 |
| [T-2.1.x](TASKS.md#feature-f-21--pydantic-contracts) | TC-API-001, TC-API-002, TC-FAIL-007 |
| [T-2.2.x](TASKS.md#feature-f-22--dual-query-embedding) | TC-RRF-001, TC-RRF-002 |
| [T-2.3.1](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) | TC-RRF-003, TC-RRF-004, TC-PERF-002, TC-FAIL-006 |
| [T-2.3.2](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) | TC-RRF-005, TC-RRF-006 |
| [T-2.3.3](TASKS.md#feature-f-23--rrf-fusion-via-universal-query-api) | TC-RRF-007, TC-FAIL-003 |
| [T-2.4.1](TASKS.md#feature-f-24--lineage-join) | TC-GRAPH-002, TC-GRAPH-005, TC-FAIL-005 |
| [T-2.5.x](TASKS.md#feature-f-25--rrf-rank-shift-validator) | TC-DEMO-001, TC-DEMO-002, TC-DEMO-003 |
| [T-3.1.x](TASKS.md#feature-f-31--react-shell) | TC-UI-001, TC-UI-002 |
| [T-3.2.x](TASKS.md#feature-f-32--weight-slider--rrf-visibility) | TC-UI-003, TC-UI-004, TC-DEMO-004 |
| [T-3.3.x](TASKS.md#feature-f-33--failure-surfaces) | TC-UI-005, TC-UI-006, TC-FAIL-003 |
| [T-3.4.1](TASKS.md#feature-f-34--demo-capture) | TC-DEMO-005 |
| [T-X.1](TASKS.md#cross-cutting-spans-all-sprints) | TC-DISC-001 |
| [T-X.2](TASKS.md#cross-cutting-spans-all-sprints) | TC-DISC-003 |
