# MemeRadar — Operational Manual

> Multi-vector, multi-modal meme discovery engine. Built for the Qdrant "Think Outside the Bot" Hackathon.
>
> Companion documents: [CLAUDE.md](CLAUDE.md) · [TASKS.md](TASKS.md) · [TESTS.md](TESTS.md)

---

## 1. System Prerequisites Installation Matrix

Native binaries only. No Docker. See [CLAUDE.md §3 System Rules](CLAUDE.md#3-system-rules--engineering-constraints) for the rationale behind the no-container constraint.

| Component | Version | Port | Purpose | Spec ref |
|---|---|---|---|---|
| Python | ≥ 3.11 | — | Backend runtime | [CLAUDE.md §1](CLAUDE.md#1-repository-file-tree) |
| uv | ≥ 0.5 | — | Python package & venv manager | [CLAUDE.md §1](CLAUDE.md#1-repository-file-tree) |
| Node.js | ≥ 20 LTS | — | Frontend toolchain | [CLAUDE.md §1](CLAUDE.md#1-repository-file-tree) |
| Qdrant | ≥ 1.12 | 6333 / 6334 | Vector store | [CLAUDE.md §2.2](CLAUDE.md#22-qdrant-named-vector-point-mapping) |
| Neo4j Community | ≥ 5.20 | 7687 / 7474 | Graph store | [CLAUDE.md §2.3](CLAUDE.md#23-fastapi-search-schema) |
| Tesseract OCR | ≥ 5.3 | — | Image text extraction | [CLAUDE.md §2.1](CLAUDE.md#21-mistral-decoder-output-schema) |

### 1.1 macOS (Homebrew)

```bash
brew install python@3.11 node tesseract uv
brew install qdrant
brew install neo4j

brew services start neo4j
neo4j-admin dbms set-initial-password changeme
```

Qdrant runs in the foreground with `qdrant` after install (binary auto-creates `./storage`).

### 1.2 Ubuntu Linux (apt)

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip tesseract-ocr

curl -LsSf https://astral.sh/uv/install.sh | sh

curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

curl -L https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo mv qdrant /usr/local/bin/qdrant

wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
echo 'deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update && sudo apt install -y neo4j
sudo neo4j-admin dbms set-initial-password changeme
sudo systemctl enable --now neo4j
```

### 1.3 Verification

```bash
tesseract --version
qdrant --version
cypher-shell -u neo4j -p changeme "RETURN 1"
python3.11 --version
uv --version
node --version
```

All six must exit 0. Verified by [TESTS.md §1 — TC-ENV-001](TESTS.md#1-pipeline-extraction-tests).

### 1.4 Managed cloud datastores (alternative to local Qdrant + Neo4j)

You can point MemeRadar at **Qdrant Cloud** and **Neo4j Aura** instead of running the local binaries — the only contract is the connection settings in `backend/.env`. This repo's reference deployment runs this way:

```bash
# backend/.env
QDRANT_URL=https://<cluster-id>.<region>.aws.cloud.qdrant.io
QDRANT_API_KEY=<qdrant-cloud-api-key>
NEO4J_URI=neo4j+s://<db-id>.databases.neo4j.io
NEO4J_PASSWORD=<aura-password>
```

When using managed cloud you **skip the Qdrant/Neo4j install rows above and Phase 1's `qdrant` / `neo4j console` terminals** — only the FastAPI process (and, in dev, the Vite server) runs locally. The "No Docker" rule ([CLAUDE.md §3.5](CLAUDE.md#3-system-rules--engineering-constraints)) governs repo files, not where your datastores live.

---

## 2. Environment Configuration Interface

Single source of truth lives in `backend/.env`. Schema is enforced at boot by `backend/config.py` — see [CLAUDE.md §1](CLAUDE.md#1-repository-file-tree) for module location.

| Variable | Required | Default | Description | Used by |
|---|---|---|---|---|
| `REDDIT_CLIENT_ID` | yes | — | Reddit OAuth app ID | `scripts/crawl_reddit.py` |
| `REDDIT_CLIENT_SECRET` | yes | — | Reddit OAuth secret | `scripts/crawl_reddit.py` |
| `REDDIT_USER_AGENT` | no | `memeradar/0.1` | UA string | `scripts/crawl_reddit.py` |
| `SUBREDDIT` | no | `memes` | Target subreddit | `scripts/crawl_reddit.py` |
| `TIME_FILTER` | no | `year` | praw time window | `scripts/crawl_reddit.py` |
| `LIMIT` | no | `1000` | Max posts | `scripts/crawl_reddit.py` |
| `QDRANT_URL` | no | `http://localhost:6333` | Qdrant endpoint | `backend/clients.py` |
| `QDRANT_API_KEY` | no | empty | For Qdrant Cloud | `backend/clients.py` |
| `QDRANT_COLLECTION` | no | `memeradar` | Collection name | `backend/clients.py` |
| `TL_API_KEY` | yes | — | Twelve Labs key | `backend/clients.py` |
| `TL_MODEL` | no | `Marengo-retrieval-2.7` | Embed model | `backend/clients.py` |
| `MISTRAL_API_KEY` | yes | — | Mistral key | `backend/clients.py` |
| `MISTRAL_CHAT_MODEL` | no | `mistral-large-latest` | Decoder model | `backend/decoder.py` |
| `MISTRAL_EMBED_MODEL` | no | `mistral-embed` | Irony embed | `backend/clients.py` |
| `NEO4J_URI` | no | `bolt://localhost:7687` | Bolt endpoint | `backend/clients.py` |
| `NEO4J_USER` | no | `neo4j` | Auth user | `backend/clients.py` |
| `NEO4J_PASSWORD` | yes | — | Auth password | `backend/clients.py` |
| `COGNEE_LLM_API_KEY` | no | falls back to `MISTRAL_API_KEY` | KG enrichment LLM | `backend/enrich_cognee.py` |
| `DATA_DIR` | no | `./data` | Local asset mount | `backend/config.py` |
| `MUTATION_MIN_MEMBERS` | no | `5` | Min template members before drift is computed (else `accumulating baseline`) | `scripts/compute_mutation_metrics.py` |
| `MUTATION_VELOCITY_THRESHOLD` | no | `0.15` | Drift velocity above which a template is flagged `trending_mutation` | `scripts/compute_mutation_metrics.py` |
| `MUTATION_HISTORICAL_WINDOW_DAYS` | no | `7` | Days before a centroid ages into the historical baseline | `scripts/compute_mutation_metrics.py` |

The boot validation contract is specified in [CLAUDE.md §3.4 Configuration Loading](CLAUDE.md#3-system-rules--engineering-constraints). Validated by [TESTS.md §1 — TC-ENV-002](TESTS.md#1-pipeline-extraction-tests).

---

## 3. Phased Execution Commands

Each phase maps directly to a sprint in [TASKS.md](TASKS.md).

### Phase 0 — One-time bootstrap

```bash
git clone <repo> memeradar && cd memeradar

uv sync

cp backend/.env.example backend/.env

cd frontend && npm install && cd ..
```

`uv sync` reads `pyproject.toml` + `uv.lock`, provisions a Python 3.11 interpreter if missing, materializes `.venv/`, and installs the locked dependency set. Re-running it is the idempotent way to refresh the environment.

### Phase 1 — Spin up local datastores

Open three terminals. See [TASKS.md Sprint 1 → T-1.1](TASKS.md#sprint-1--ingestion--storage-days-13).

```bash
qdrant
neo4j console
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**One-command backend start.** The third line — plus `uv sync` — is packaged into a single startup command:

```bash
./start.ps1            # Windows (PowerShell)
./start.sh             # bash
```

It runs `uv sync` then launches `uvicorn backend.main:app` on `:8000`. Flags: `-Port 9000` / `--port=9000`, hot-reload with `-Reload` / `--reload`, and `-BuildFrontend` / `--build-frontend` to also build the SPA into `frontend/dist` and serve UI + API on the one port. (Without that flag the SPA is served only if `frontend/dist` already exists — see [Phase 3](#phase-3--serve-the-react-ui) for the dev UI.)

> **Using managed cloud ([§1.4](#14-managed-cloud-datastores-alternative-to-local-qdrant--neo4j))?** `./start.ps1` is the *only* process you run — Qdrant Cloud and Neo4j Aura are already up, there are no local `qdrant` / `neo4j console` terminals, and the local `healthz` probes below do not apply.

Health checks (a fourth terminal):

```bash
curl -s http://localhost:6333/healthz                 # local Qdrant only
curl -s -u neo4j:changeme http://localhost:7474       # local Neo4j only
curl -s http://localhost:8000/health                  # always — expect {"status":"ok"}
```

### Phase 2 — Crawl and ingest

Maps to [TASKS.md Sprint 1 → T-1.2, T-1.3, T-1.4](TASKS.md#sprint-1--ingestion--storage-days-13).

```bash
uv run python -m scripts.crawl_reddit

uv run python -m backend.ingest --workers 4 --limit 50

uv run python -m backend.ingest --workers 4

uv run python -m backend.enrich_cognee
```

The first ingest pass uses `--limit 50` to validate end-to-end before burning the full Twelve Labs quota. See [TESTS.md §1 — TC-ING-005](TESTS.md#1-pipeline-extraction-tests).

### Phase 3 — Serve the React UI

Maps to [TASKS.md Sprint 3 → T-3.1, T-3.2](TASKS.md#sprint-3--ui-delivery--integration-days-78).

```bash
cd frontend
echo "VITE_API=http://localhost:8000" > .env
npm run dev
```

Open `http://localhost:5173`. (Vite auto-increments to `5174`+ if `5173` is taken.)

### Phase 4 — Mutation Radar (optional)

Maps to [TASKS.md Sprint 5 → F-5.1](TASKS.md#sprint-5--meme-mutation-radar). Quantifies each template's visual **drift velocity** relative to its spherical-mean centroid, in a decoupled batch step so the hot `/search` path never runs dense-vector arithmetic.

```bash
uv run python scripts/compute_mutation_metrics.py
```

The batch computes a spherical-mean `centroid_visual` per template (→ Neo4j), writes each point's `template_drift_score` + `trending_mutation` flag (→ Qdrant), and raises `trending_mutation` when a template's drift velocity over the last `MUTATION_HISTORICAL_WINDOW_DAYS` exceeds `MUTATION_VELOCITY_THRESHOLD`. Templates with fewer than `MUTATION_MIN_MEMBERS` members are held as `accumulating baseline` (velocity `0.0`). It makes **no embedding-API calls**, so it is safe and cheap to re-run.

Read the pre-computed metrics (graph-only — no dense arithmetic on the hot path):

```bash
curl -s 'http://localhost:8000/mutations' | python -m json.tool
curl -s 'http://localhost:8000/mutations?trending_only=true' | python -m json.tool
```

`GET /mutations` returns one row per template (`member_count`, `velocity`, `trending_mutation`, `accumulating_baseline`) plus the active `threshold` and `min_members`.

---

## 4. Live Demo & RRF Validation Script

Engineering walkthrough that doubles as the 3-minute demo video script. Covers [TESTS.md §2 — RRF rank-shift suite](TESTS.md#2-vector-search-fusion-tests) end-to-end.

### 4.1 Demo Query

```
absolute panic when production crashes
```

### 4.2 Manual RRF Sweep Procedure

Open the UI at `http://localhost:5173`. Drag the visual/irony slider through the five positions below in order and capture the **top-5 meme IDs** at each step.

| Step | Visual | Irony | Expected top-1 trait | API call (for reproducibility) |
|---|---|---|---|---|
| A | 1.00 | 0.00 | Pure visual: wide-eyed, panicked facial expression | `GET /search?q=...&visual_weight=1.0&irony_weight=0.0&k=5` |
| B | 0.75 | 0.25 | Mostly visual, irony begins to filter | `...&visual_weight=0.75&irony_weight=0.25` |
| C | 0.50 | 0.50 | Balanced — joke about panic + visual cue | `...&visual_weight=0.5&irony_weight=0.5` |
| D | 0.25 | 0.75 | Mostly semantic — dev/sysadmin context dominates | `...&visual_weight=0.25&irony_weight=0.75` |
| E | 0.00 | 1.00 | Pure irony: textually exact, may be visually mild | `...&visual_weight=0.0&irony_weight=1.0` |

### 4.3 RRF Validation Assertions

For the sweep to count as a passing demo, the operator must verify:

1. **Rank shift is observable.** The top-1 result at step A ≠ top-1 at step E. Hard fail otherwise.
2. **Monotonic transition.** Result sets at adjacent steps share more IDs with their neighbour than with the opposite extreme (Jaccard(A, B) > Jaccard(A, E)).
3. **No empty pages.** Every step returns ≥ 5 results. Empty-result handling is specified by [TESTS.md §2 — TC-RRF-007 Zero Result](TESTS.md#2-vector-search-fusion-tests).
4. **Lineage panel populates** on every result click. Failures here mean Neo4j was not enriched — see [TESTS.md §3 — TC-GRAPH-002](TESTS.md#3-graph-lineage-validation).

### 4.4 Validation Script Hook

Programmatic equivalent of the manual sweep, used by CI:

```bash
uv run python -m scripts.rrf_sweep --query "absolute panic when production crashes" --k 5
```

Behavior contract: emits a JSON report with the five top-k lists and the Jaccard matrix. Exit code 0 only if assertions 1–3 above hold. Implementation scope is specified in [TASKS.md Sprint 2 → T-2.5](TASKS.md#sprint-2--search-fusion-engine-days-46).
