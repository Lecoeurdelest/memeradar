#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

NODE_BIN="/tmp/node-v22.14.0-darwin-arm64/bin"
if [ -d "$NODE_BIN" ]; then
  export PATH="$NODE_BIN:$PATH"
fi

if ! command -v npm &>/dev/null; then
  echo "ERROR: npm not found. Re-extract Node.js into /tmp/node-v22.14.0-darwin-arm64/ or install it." >&2
  exit 1
fi

echo "=== Building frontend (always fresh dist) ==="
(
  cd frontend
  [ -d node_modules ] || npm install
  VITE_API=http://localhost:8000 npm run build
)

echo "=== Starting server on http://localhost:8000 (backend + frontend) ==="
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000