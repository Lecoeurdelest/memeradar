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
