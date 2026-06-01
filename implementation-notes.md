# Implementation Notes — KSP 1

> Running log for the **Meme Mutation Radar** build. Captures every decision, change,
> and tradeoff that was *not* spelled out in the spec. Source files carry no comments
> per [CLAUDE.md §3.1](MemeFinder/CLAUDE.md); all such commentary lives here.

## Architectural Decisions Made (Not in Spec)

- **New pure-math module `backend/mutation.py`.** The spec lists a "spherical mean
  mathematics module" as a subtask but does not name a file. I isolated all vector
  arithmetic (L2 normalize, spherical mean, cosine distance) into `backend/mutation.py`
  with **zero vendor imports** (`math` only). This keeps it outside the Qdrant/Neo4j
  vendor-boundary rules ([CLAUDE.md §3.6](MemeFinder/CLAUDE.md)) and makes it unit-testable
  with no datastore running.
- **Vendor boundaries preserved.** The batch script `scripts/compute_mutation_metrics.py`
  touches **no** vendor SDK directly. All Qdrant and Neo4j access goes through new helpers
  added to `backend/clients.py` (the sanctioned owning module). Qdrant is also permitted in
  `backend/search.py`, but the new read path lives in `clients.py` to stay closest to the
  existing helper conventions.
- **`indexed_at` is now written at ingest time.** The spec asks for an integer index on
  `indexed_at` but the existing payload never populated it. I added
  `"indexed_at": int(time.time())` to the ingest payload in `backend/ingest.py` so the index
  is meaningful going forward. Pre-existing points without it are tolerated (the field is
  optional in the schema and the script does not require it for centroid/velocity math).
- **Two extra Neo4j `:MemeTemplate` properties beyond the spec list.** The spec mandates
  `centroid_visual`, `historical_centroid_visual`, and `velocity`. To implement the
  "7-days-prior" comparison and to power a cheap read endpoint without re-scanning Qdrant,
  I also persist `centroid_computed_at` (Unix ts of the last centroid write) and
  `member_count`. Both are auxiliary; the three spec'd properties remain authoritative.
- **New read-only endpoint `GET /mutations`.** Target #4 asks for "endpoints" and the
  objective mentions "visualize," but no endpoint contract is defined. I added one minimal,
  read-only endpoint that serves the *pre-computed* Neo4j metrics (velocity, member count,
  derived trending/accumulating flags). It performs **no dense-vector arithmetic** — it is an
  O(templates) graph read — so it honors the spec's "protect the hot search path" intent.
  Supports `?trending_only=true`.
- **Schema migration runs both on boot and in the script.** `ensure_mutation_indexes()` is
  idempotent (each `create_payload_index` is wrapped in try/except, mirroring the existing
  `ensure_sha256_index`) and is invoked from the FastAPI `lifespan` *and* at the top of the
  batch script, so the migration applies regardless of which entry point runs first.

## Mathematics & Algorithm Refinements

- **Spherical Mean** is implemented exactly as specified:
  `normalize(mean_i(normalize(v_i)))`. Three explicit passes — per-vector L2 normalize,
  arithmetic mean of the unit components, then a final L2 renormalize of the mean back onto
  the unit hypersphere.
- **Zero-vector handling.** `l2_normalize` returns the zero vector unchanged when its norm is
  `0.0` (no division-by-zero). Consequently `cosine_distance` returns `1.0` (maximal distance)
  whenever either operand has zero norm — an undefined direction is treated as maximally
  divergent rather than raising.
- **Degenerate centroid edge case.** If the unit vectors of a cluster sum to (near) zero
  (e.g. perfectly antipodal members), the renormalized centroid collapses to the zero vector
  and is *not* unit length. This is mathematically unavoidable for the spherical mean and is
  documented here rather than masked; real visual clusters are not antipodal, so the unit-length
  invariant (TC-VEC-003) holds for any realistic sample.
- **Cosine clamp.** Floating-point error can push the cosine similarity slightly outside
  `[-1, 1]`; it is clamped before computing `distance = 1 - similarity`, guaranteeing
  `drift_score ∈ [0, 2]`.
- **`velocity` definition.** The spec leaves "drift velocity" of a template under-specified.
  I define it as the **cosine distance between the current centroid and the historical
  centroid** (centroid displacement on the hypersphere). `trending_mutation` is then
  `velocity > MUTATION_VELOCITY_THRESHOLD` for eligible templates.

## Structural Modifications & Code Tradeoffs

- **Threshold as a central config var vs. "hardcoded".** The spec calls for a "hardcoded
  experimental threshold," but [CLAUDE.md §3.4](MemeFinder/CLAUDE.md) requires configuration via
  central variables. I reconciled this by defining `MUTATION_VELOCITY_THRESHOLD` in
  `backend/config.py` with a baked default (`0.15`) and an env override — effectively hardcoded
  in the default path, but rule-compliant. `MUTATION_MIN_MEMBERS` (5),
  `MUTATION_HISTORICAL_WINDOW_DAYS` (7), `MUTATION_SCROLL_BATCH`, and
  `MUTATION_UPSERT_CONCURRENCY` are centralized the same way.
- **Concurrency model.** Templates are processed **sequentially** (outer loop) so a single
  template's full member set is in memory at once and Neo4j writes are ordered; the
  **per-member Qdrant `set_payload` writes are fanned out concurrently** under a bounded
  `asyncio.Semaphore(MUTATION_UPSERT_CONCURRENCY)`. This matches the strict-async rule
  ([CLAUDE.md §3.2](MemeFinder/CLAUDE.md)) and the existing ingest fan-out pattern, while
  capping concurrent load on Qdrant during the update pass.
- **Partial payload updates, not full upserts.** Drift/trending writes use Qdrant
  `set_payload` (additive) rather than re-`upsert`-ing the whole point. This avoids
  re-sending the 1024-dim vectors and cannot accidentally clobber existing payload fields —
  important because the batch step runs decoupled from ingest.
- **Test-ID collision (important).** The spec requested test IDs `TC-VEC-002` and
  `TC-FAIL-007`, but **both already exist** in [TESTS.md](MemeFinder/TESTS.md)
  (TC-VEC-002 = ingest idempotency, referenced from CLAUDE.md §2.2; TC-FAIL-007 = oversized
  query). Overwriting referenced cases would break traceability, so I added the requested
  assertions under the next free IDs: **`TC-VEC-003`** (unit-length centroid) and
  **`TC-FAIL-009`** (small-sample zero-velocity guardrail), and updated the coverage dashboard
  counters accordingly.

## Verification & Edge Cases

All checks below ran on 2026-06-01 (Windows, Python 3.12 via `uv run`). Qdrant/Neo4j were
**not** running, so datastore I/O was exercised via in-process mocks; the math and control flow
are real.

- **Compile gate.** `python -m py_compile` clean across all touched files
  (`mutation.py`, `clients.py`, `config.py`, `schemas.py`, `ingest.py`, `main.py`,
  `compute_mutation_metrics.py`).
- **Discipline gate (CLAUDE.md §3.1).** Comment/docstring grep over the two new files and the
  four edited backend modules: **zero** `#` comments or docstrings. `schemas.py` uses only the
  whitelisted `Field(description=...)`.
- **App wiring.** `import backend.main` succeeds under the synced env; the `/mutations` route is
  registered. `config.MUTATION_*` constants load (MIN=5, THRESHOLD=0.15, WINDOW=7).
- **Spherical mean — unit length (TC-VEC-003).** On a realistic 7-member cluster the centroid's
  `L2 == 1.0` (to 1e-12). `cosine_distance(c, c) == 0.0`. `cosine_distance` of a zero vector
  returns `1.0` (no crash). `spherical_mean([]) == []`.
- **Small-sample guardrail (TC-FAIL-009).** Mock execution of `process_template` with a 3-member
  template returns `velocity == 0.0`, `trending == false`, status `accumulating_baseline`,
  persists **no** centroid, and the Qdrant writes for those members set **only**
  `trending_mutation = false` (velocity computation bypassed) — no exception raised.
- **Normal path.** A 6-member template computes a unit-length centroid and emits one Qdrant
  `set_payload` per member carrying both `template_drift_score` and `trending_mutation`.
- **First-run velocity.** With no historical centroid on the first run, `velocity` is `0.0` by
  design (displacement needs a prior snapshot); it becomes non-zero only after a snapshot ages
  past `MUTATION_HISTORICAL_WINDOW_DAYS`. This is expected, not a bug.
- **Not yet exercised:** a true end-to-end run against live Qdrant + Neo4j and the `GET /mutations`
  HTTP round-trip. Tracked in `progress.md`; F-5.1 remains `in-progress` until that run is green.

## Frontend (KSP 1 UI) Decisions — Meme Mutation Radar Panel

> Detailed UI-specific rationale lives in [implementation-notes-ui.html](implementation-notes-ui.html);
> the load-bearing decisions are summarized here so this file stays the single decision log.

- **New component module, no new dependency.** Added `frontend/src/components/MutationRadar.jsx`
  (+ `MutationRadar.css`) composed of semantic sub-components `TrendVelocityBadge`,
  `DriftVectorGauge`, `VelocityGraph`, `SmallSampleNotice`, and `EvolutionTimeline`. Gauges are
  pure-CSS meters and the lineage "vector cluster" is an inline `<svg>` scatter — `package.json`
  is unchanged (no chart library), honoring the spec's "lightweight" directive.
- **Payload mapping lives in the API client layer.** `frontend/src/api.js` gains `fetchMutations`,
  `buildMutationIndex`, and `toMutationRadarModel`, which normalize `template_drift_score`,
  `trending_mutation`, and `lineage_cache` (accepting both the spec name `lineage_cache` and the
  live backend field `lineage`) into one radar model with safe defaults.
- **State model.** A single `mutationIndex` state is hydrated once on mount via `useEffect` →
  `/mutations`; the per-meme radar model is *derived* (not stored) from the selected hit, so there
  is no telemetry duplication or extra render state.
- **Small-sample guardrail is data-driven.** `accumulatingBaseline` is true when the matched
  template reports `accumulating_baseline` or `member_count < min_members` (`min_members` read from
  the `/mutations` response, default 5). The container hard-swaps the live velocity graph for the
  "Accumulating baseline data…" banner — replacement, not hiding. Asserted by `TC-UI-007`.
- **Drift gauge scale.** Spec labels the gauge `0.0 → 1.0`; the backend cosine drift score is
  bounded `[0, 2]`. The gauge keeps the spec's 0–1 labeled scale, clamps the fill to `[0, 1]`, and
  prints the raw value with a Canonical/Drifting/High-Irony zone readout. `/search` does not yet
  surface per-meme `template_drift_score`, so it is mapped defensively and shows the null state
  rather than a fabricated number.
- **Graceful degradation.** A failed `/mutations` fetch resolves to an empty index; missing
  telemetry yields the standard null-lineage values (Stable Format badge, "telemetry unavailable"
  gauge/velocity, hit-derived or empty lineage), never a throw — mirroring
  [CLAUDE.md §2.3 invariant 5](CLAUDE.md#23-fastapi-search-schema).
- **Test-ID collision (same pattern as TC-VEC / TC-FAIL above).** The spec requested `TC-UI-001`
  and `TC-UI-002`, but both already exist (cold-start search; grid responsiveness) and are
  referenced by the traceability matrix. The new cases land at the next free IDs — **`TC-UI-007`**
  (accumulating-baseline banner) and **`TC-UI-008`** (Trend Velocity badge) — with the coverage
  dashboard and matrix updated.
- **Build verification caveat.** The Vite/esbuild bundler could not be run in the authoring
  sandbox (subprocess spawns hang and orphan); the frontend was validated by review. `npm run build`
  in `frontend/` should be run on a normal host to confirm the production bundle.

## Outstanding / Pre-existing Notes

- `backend/storage.py` (S3 helpers) predates this work and was already absent from the CLAUDE.md
  §1 file tree; I left that pre-existing drift untouched to keep this change scoped to KSP 1.
