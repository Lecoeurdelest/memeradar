# AGENTS.md — Agent Routing Layer

MemeRadar is a multi-vector, multi-modal meme search engine (Qdrant + Neo4j + Mistral + Twelve Labs). This file is the entry point for any AI coding agent or new teammate. Keep it short — link, don't restate.

## Startup Workflow

Before touching code, in order:

1. Read this file end to end.
2. Read [CLAUDE.md](CLAUDE.md) — hard contracts, file tree, vendor boundaries, no-comment rule.
3. Skim [feature_list.json](feature_list.json) to know what's `done` / `in-progress` / `todo`.
4. Read the tail of [progress.md](progress.md) for session continuity (last 3 entries minimum).
5. Run `./init.ps1` (Windows) or `./init.sh` (bash) — bootstraps the venv via uv, installs frontend deps, runs health probes.
6. Only then start coding.

## Required Reading by Task Type

| If you're changing... | Also read |
|---|---|
| Pydantic schemas / API contract | [CLAUDE.md §2](CLAUDE.md#2-interface--data-specifications) |
| Ingestion pipeline | [CLAUDE.md §3.2](CLAUDE.md#32-async-processing-loops), [CLAUDE.md §3.3](CLAUDE.md#33-determinism--idempotency) |
| Adding a new vendor call | [CLAUDE.md §3.6 vendor boundaries](CLAUDE.md#36-vendor-boundaries) — single-module rule |
| Search / RRF | [README.md §4 RRF validation](README.md#4-live-demo--rrf-validation-script) + `scripts/rrf_sweep.py` |
| Anything else | the matching row in [TASKS.md](TASKS.md) |

## Working Rules

- **One feature at a time.** Pick one `in-progress` (or promote one `todo`) in `feature_list.json` and finish it before starting another.
- **Application code carries no comments or docstrings.** Enforced by [CLAUDE.md §3.1](CLAUDE.md#31-comment--docstring-prohibition-application-code). The only exempt files are `pyproject.toml` and `.env.example`.
- **Vendor SDKs are containerized to one module each.** See [CLAUDE.md §3.6](CLAUDE.md#36-vendor-boundaries). No exceptions.
- **Idempotent or it's broken.** Ingest reruns must be no-ops (Qdrant `uuid5` IDs, Neo4j `MERGE`).
- **No Docker.** Native binaries only — see [README.md §1](README.md#1-system-prerequisites-installation-matrix).
- **Dependencies are managed by `uv`.** `pip install` directly into `.venv` is forbidden; edit `pyproject.toml` and `uv sync`.

## Verification

A change is not "done" until ALL of the following hold:

1. `./init.ps1` (or `./init.sh`) exits 0.
2. `uv run python -c "import backend.main"` exits 0.
3. `curl http://localhost:8000/health` returns `{"status":"ok"}`.
4. The TESTS.md cases referenced from the matching TASKS.md row pass.
5. No new `import` of a vendor SDK appears outside its owning module ([CLAUDE.md §3.6](CLAUDE.md#36-vendor-boundaries)).
6. No new `#` comment or docstring appears under `backend/` or `scripts/`.

If you can't run a check (e.g. Twelve Labs quota exhausted), say so explicitly in `progress.md`. Do not claim green.

## Definition of Done

A feature in `feature_list.json` flips to `done` only when:

- [ ] All sub-tasks in the matching TASKS.md row are `[x]`.
- [ ] Tests listed for those tasks pass locally.
- [ ] `evidence` field in `feature_list.json` is filled in (commit SHA, test names, or "manual <date>").
- [ ] `progress.md` has a session entry describing what shipped and what's next.

## End of Session Checklist

Before you stop:

1. Update `progress.md` — append a new dated entry: what changed, what's still open, blockers.
2. Update `feature_list.json` — flip statuses, fill `evidence` for anything completed.
3. If a future agent will pick this up cold, fill `session-handoff.md`.
4. Commit with a message that names the feature ID (e.g. `feat(F-4.2): batch translate captions`).
5. Confirm `git status` is clean (or every dirty file is named in `session-handoff.md`).

## Required Artifacts

- `AGENTS.md` — this file
- `CLAUDE.md` / `README.md` / `TASKS.md` / `TESTS.md` — contracts, ops, sprints, QA
- `feature_list.json` — machine-readable state tracker
- `progress.md` — append-only session log
- `session-handoff.md` — populated only when handing off mid-feature
- `init.ps1` / `init.sh` — idempotent bootstrap + health check
- `start.ps1` / `start.sh` — single backend startup command (`uv sync` + uvicorn on `:8000`; `-BuildFrontend`/`--build-frontend` to also serve the SPA)
- `pyproject.toml` + `uv.lock` + `.python-version` — Python env contract
