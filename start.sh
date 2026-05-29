#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Building frontend (always fresh dist) ==="
(
  cd frontend
  [ -d node_modules ] || npm install
  VITE_API=http://localhost:8000 npm run build
)

echo "=== Starting server on http://localhost:8000 (backend + frontend) ==="
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000