# progress.md — Session Continuity Log

Append-only. Newest entries at the top. Every session ends with an entry per AGENTS.md.

Format:
```
## YYYY-MM-DD — <short title>
**Agent/Author:** <name or claude-opus-4.7>
**Shipped:** <bullets>
**Open:** <bullets>
**Blockers:** <bullets or "none">
**Next session should:** <one or two sentences>
```

---

## 2026-06-01 — Single backend startup command (start.ps1 / start.sh)

**Agent/Author:** claude-opus-4.8
**Shipped:**
- Packaged backend startup into one command. **Repurposed** the pre-existing `start.ps1` / `start.sh` (which silently did *single-port*: build frontend every run + serve on :8000 — and `start.sh` hardcoded a macOS Node path, so it was broken on Windows) into a **backend-only** default per the user's choice: `uv sync` → `uvicorn backend.main:app` on `:8000`.
  - Params: `-BindHost`/`-Port`/`-Reload` (ps1), `--host=`/`--port=`/`--reload` + `MEMERADAR_HOST`/`MEMERADAR_PORT` (sh).
  - The old build-and-serve behavior is preserved as an **opt-in** flag (`-BuildFrontend` / `--build-frontend`) so nothing was lost.
  - `start.sh` now uses `uv run uvicorn` (cross-platform) instead of the Unix-only `.venv/bin/python`, so it works under Windows git-bash too.
- Verified: `start.ps1` ran end-to-end on a scratch port (uv sync → uvicorn → `/health` 200); `start.sh` passed `bash -n` + arg-parse dry run.
- Docs: README Phase 1 now features the one-command start (and notes it's the *only* process under managed cloud); `init.ps1`/`init.sh` "Start app" hints point to `./start.*`; AGENTS.md Required Artifacts lists `start.ps1`/`start.sh`.

**Open:** none for this task. (Frontend dev server is still a separate `npm run dev` by design — user chose backend-only.)

**Blockers:** none.

**Next session should:** Unchanged — reconcile the 512-vs-1024 visual-vector dimension, then F-4.2 / F-X.1.

---

## 2026-06-01 — Full-stack live run + README accuracy pass

**Agent/Author:** claude-opus-4.8
**Shipped:**
- **Ran the whole app live.** Backend `uv run uvicorn backend.main:app --port 8000` against the cloud datastores; Vite dev UI (`npm run dev`, landed on :5174 since :5173 was already in use). Drove every core surface against live cloud data:
  - `GET /health` → ok; `GET /random?k=3` → real memes with populated Neo4j lineage; `GET /mutations` → 103 templates.
  - `GET /search?q=absolute panic when production crashes` → RRF dual-vector fusion returned 5 descending-score hits (0.643→0.250) with templates, jokes, psychological_state, and lineage — the core feature works end-to-end (one Twelve Labs + one Mistral query embedding per call).
  - **UI screenshot** (headless Chrome): header + search bar + visual/irony slider + language pills + responsive grid of real meme images with template labels. Confirmed not a blank frame.
- **README.md accuracy pass:** added §1.4 *Managed cloud datastores* (Qdrant Cloud + Neo4j Aura via `.env`; this is the reference deployment) clarifying you skip the local `qdrant`/`neo4j console` terminals; added the `MUTATION_*` env knobs to the §2 config table; annotated Phase 1 health checks as local-only; added **Phase 4 — Mutation Radar** (`compute_mutation_metrics.py` + `GET /mutations`); noted Vite's port auto-increment.

**Open:**
- Same as below: 512-vs-1024 visual-vector dim drift to reconcile; F-3.4 / F-4.2 / F-X.* still open.

**Blockers:** none.

**Next session should:** Reconcile the visual-vector dimension (CLAUDE.md §2.2 says 1024; live data is 512), then pick up F-4.2 or F-X.1.

---

## 2026-06-01 — F-5.1 CLOSED: live end-to-end against Qdrant Cloud + Neo4j Aura

**Agent/Author:** claude-opus-4.8
**Shipped:**
- **F-5.1 flipped to `done`.** Ran the full live end-to-end. Key discovery: the datastores are **remote cloud** (Qdrant Cloud `…cloud.qdrant.io`, Neo4j Aura `…databases.neo4j.io`), not local — so no Docker/native bring-up was needed, and the collection was **already populated** (106 points, named vectors `visual`+`irony`; Aura had 104 Meme / 103 MemeTemplate nodes, 0 centroids).
- `backend.ingest` was **skipped on purpose**: `data/images` is empty, so every manifest entry would early-return as `image_missing` (before any API call — zero spend, zero new points). The existing 106-point collection is the populated collection the Sprint 5 criteria require.
- **`scripts/compute_mutation_metrics.py` against live cloud:** 103 templates, `0 errors`. Every template has exactly 1 member (decoder produced very granular template names) → all hit the small-sample guardrail (`accumulating_baseline`, velocity 0.0) — **TC-FAIL-009 live**. `neo4j_set_template_centroid` + `qdrant_set_payload_fields` executed against real cloud.
- **`GET /mutations` HTTP round-trip** (uvicorn on :8011, `/health` ok): returned 103 templates with correct schema (`member_count`/`velocity`/`trending_mutation`/`accumulating_baseline`); `?trending_only=true` → 0.
- **Computed/trending path** (no real template has ≥5 members) closed two ways: (a) in-memory real-Qdrant-engine integration — 6-member unit centroid + 7-day-aged history → velocity `0.951` > `0.15` → `trending=True` propagated to members; (b) a `MUTATION_MIN_MEMBERS=1` live verification run that persisted real unit-length `centroid_visual` arrays to Aura + `template_drift_score` to cloud Qdrant, read back (L2==1.0), then **reverted to the MIN=5 default** (0 centroids, 103 accumulating) so production reflects an operator-faithful default run.

**Open:**
- **Spec-vs-data drift (not F-5.1):** live visual vectors are **512-dim**, but CLAUDE.md §2.2 / `clients.py TL_VECTOR_DIM` declare 1024. Mutation math is dimension-agnostic (unaffected), but ingest/collection dim should be reconciled with the spec in a follow-up.
- Minor residue: the MIN=1 verification left `template_drift_score=0.0` on the 106 points (the accumulating path only rewrites `trending_mutation`, never clears drift). Values are truthful (single-member self-distance) and unused by `/mutations`; a from-scratch MIN=5 run would leave them `None`.
- F-3.4 (demo), F-4.2 (batch translate), F-X.1/F-X.2 (CI) remain the open product/harness features.

**Blockers:** none.

**Next session should:**
Reconcile the 512 vs 1024 visual-vector dimension (CLAUDE.md §2.2 + `clients.py`), or confirm 512 is intended and fix the spec. Then pick up F-4.2 or F-X.1. Mutation radar will only show `computed`/`trending` templates once any template accumulates ≥5 members.

---

## 2026-06-01 — F-5.1 verification deep-pass (real-Qdrant integration)

**Agent/Author:** claude-opus-4.8
**Shipped:**
- Re-ran the F-5.1 verification with real evidence (prior session used pure in-process mocks). All offline-runnable checks green under `uv run` on the pinned `.venv` (Python 3.11.8):
  - **Import/wiring gate:** `import backend.main` OK; `/mutations` route registered.
  - **TC-VEC-003:** 7-member spherical-mean centroid `L2 == 1.0` (to 1e-12); `cosine_distance(c,c) == 0`; zero-vector distance `== 1.0`; `spherical_mean([]) == []`; drift bound `[0,2]`.
  - **TC-FAIL-009:** small-sample threshold logic (N<5 → velocity 0.0, not trending).
  - **Discipline (CLAUDE.md §3.1):** comment/docstring grep clean on `backend/mutation.py` and `scripts/compute_mutation_metrics.py`.
- **NEW — real-Qdrant integration of the actual batch script.** Ran `compute_mutation_metrics.run()` against an in-memory Qdrant engine (`AsyncQdrantClient(location=":memory:")`) with only the two Neo4j helpers stubbed. This exercises the REAL Qdrant code paths: `ensure_mutation_indexes`, `qdrant_distinct_templates`, `qdrant_scroll_template_members` (named-vector retrieval), `qdrant_set_payload_fields`, plus `spherical_mean`, `_resolve_historical` 7-day aging, velocity/threshold, and the bounded-`Semaphore` member fan-out.
  - RUN 1 (no history): `doge` (3) → accumulating_baseline, no centroid, members forced `trending_mutation=false`, **no** drift score; `drakeposting` (6) → unit centroid, per-member `template_drift_score` written.
  - RUN 2 (prior centroid aged >7d + cluster rotated): velocity `0.951551` > `0.15` → `trending=true` propagated to all 6 members. All assertions passed.

**Open:**
- F-5.1 stays `in-progress`. Real Qdrant-engine paths now proven, but three things remain unverified and need infra/quota: (a) live Neo4j Cypher (`MERGE`/`MATCH` centroid props) over Bolt; (b) `GET /mutations` HTTP round-trip against live Neo4j; (c) a true ingest run.

**Blockers:**
- No datastores reachable this session: Qdrant (6333/6334) and Neo4j (7687/7474) not listening; Docker daemon not running; no native `qdrant`/`neo4j` on PATH. A real ingest additionally needs Mistral/TwelveLabs/Reddit API quota. Per AGENTS.md I did **not** flip F-5.1 to `done` — cannot claim green on checks I can't run.

**Next session should:**
Bring up Qdrant + Neo4j (operator decision: native binaries per README §1, or transient containers if Docker is started — note CLAUDE.md §3.5 forbids Docker *files in the repo*, not transient local containers). Then `uv run python -m backend.ingest --limit 50`, `uv run python scripts/compute_mutation_metrics.py`, and `curl /mutations` to confirm velocities + trending. Flip F-5.1 to `done` and fill evidence once that round-trip is green.

---

## 2026-06-01 — KSP 1 Meme Mutation Radar (F-5.1)

**Agent/Author:** claude-opus-4.8
**Shipped:**
- New pure-math module `backend/mutation.py` (`l2_normalize`, `spherical_mean`, `cosine_distance`, `l2_norm`) — no vendor SDK, no comments. Spherical mean = `normalize(mean(normalize(v_i)))`.
- `backend/clients.py`: `ensure_mutation_indexes` (idempotent — `indexed_at` INTEGER, `template` KEYWORD, `template_drift_score` FLOAT, `trending_mutation` BOOL), `qdrant_distinct_templates`, `qdrant_scroll_template_members` (visual vectors), `qdrant_set_payload_fields` (partial `set_payload`), Neo4j `neo4j_get_template_centroid` / `neo4j_set_template_centroid` / `neo4j_list_template_metrics`.
- `:MemeTemplate` now carries spec'd `centroid_visual` / `historical_centroid_visual` / `velocity` plus auxiliary `centroid_computed_at` + `member_count` (needed for the 7-day window and the read endpoint).
- `scripts/compute_mutation_metrics.py`: scroll-by-template → spherical-mean centroid → Neo4j write → per-member `template_drift_score` upsert to Qdrant under a bounded `Semaphore`; 7-day historical velocity → `trending_mutation`. Small-sample (`N<5`) guardrail forces velocity 0.0 / trending false / accumulating-baseline.
- `backend/schemas.py`: payload gains `indexed_at`, `template_drift_score`, `trending_mutation`; new `TemplateMutation` + `MutationRadarResponse`.
- `backend/main.py`: `ensure_mutation_indexes()` added to lifespan; new read-only `GET /mutations?trending_only=` (graph-only, no dense arithmetic on hot path).
- `backend/ingest.py`: now writes `indexed_at = int(time.time())`.
- Docs: CLAUDE.md (§1 tree, §1.1 endpoints, §2.2 payload contract), TASKS.md (Sprint 5 / F-5.1), TESTS.md (TC-VEC-003 + TC-FAIL-009, dashboards reconciled to 57). `implementation-notes.md` created at repo root.
- **Verified locally (no DB):** `backend/mutation.py` emits a unit-length centroid (L2 = 1.0) and the small-sample path returns velocity 0.0 without raising.

**Open:**
- Not yet run end-to-end against live Qdrant + Neo4j (datastores were not up this session).
- F-5.1 stays `in-progress` until `compute_mutation_metrics.py` runs against a populated collection and `GET /mutations` is exercised.

**Blockers:** none.

**Next session should:**
Start Qdrant + Neo4j, run `python -m backend.ingest --limit 50`, then `python scripts/compute_mutation_metrics.py`, and `curl /mutations` to confirm velocities + trending flags. Flip F-5.1 to `done` and fill evidence once green.

---

## 2026-05-29 — Harness scaffold + uv migration

**Agent/Author:** claude-opus-4.7
**Shipped:**
- Migrated Python toolchain from `pip + requirements.txt` to `uv` (pyproject.toml, uv.lock, .python-version pinned to 3.11). Removed `backend/requirements.txt`.
- Pinned `mistralai>=1.2,<2` — 2.x dropped the `Mistral` symbol that `backend/clients.py` imports. **Do not unpin without rewriting clients.py.**
- Verified backend boots under uv: `uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000` → `/health` returns `{"status":"ok"}`.
- Verified frontend boots: `npm run dev` in `frontend/` → Vite on :5173.
- Updated `README.md` (prereq table, verification, all `pip` / `python -m` commands → `uv sync` / `uv run python -m`).
- Updated `CLAUDE.md` file tree (added pyproject.toml, uv.lock, .python-version; removed backend/requirements.txt) and the comment-exemption list.
- Added harness layer: `AGENTS.md`, `feature_list.json`, `progress.md` (this file), `session-handoff.md` template, `init.ps1`, `init.sh`.

**Open:**
- F-3.4 (demo capture) and F-4.2 (batch translation script) are the next product features.
- F-X.1 / F-X.2 (CI lint + vendor containment) still todo.
- Qdrant and Neo4j were not running during the session — `/search` was not exercised end-to-end.

**Blockers:** none.

**Next session should:**
Start Qdrant (`qdrant`) and Neo4j (`neo4j console`), run `./init.ps1`, then either kick off F-4.2 (translate_captions.py) or F-X.1 (CI lint with the no-comments enforcement). If picking up F-4.2, read `backend/translate.py` first and copy its `SUPPORTED_LANGUAGES` set rather than redefining.
