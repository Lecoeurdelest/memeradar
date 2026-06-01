#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

HOST="${MEMERADAR_HOST:-0.0.0.0}"
PORT="${MEMERADAR_PORT:-8000}"
RELOAD=""
BUILD_FRONTEND=0
for arg in "$@"; do
  case "$arg" in
    --reload) RELOAD="--reload" ;;
    --build-frontend) BUILD_FRONTEND=1 ;;
    --host=*) HOST="${arg#*=}" ;;
    --port=*) PORT="${arg#*=}" ;;
    *) echo "WARN: ignoring unknown arg: $arg" >&2 ;;
  esac
done

echo "=== [1/2] uv sync (Python deps) ==="
uv sync

if [ "$BUILD_FRONTEND" = "1" ]; then
  echo "=== (opt-in) build frontend -> frontend/dist (served on the same port) ==="
  (
    cd frontend
    [ -d node_modules ] || npm install
    VITE_API="http://localhost:${PORT}" npm run build
  )
fi

if [ ! -f backend/.env ]; then
  echo "WARN: backend/.env not found - copy backend/.env.example and fill required keys, or boot fails fast." >&2
fi

echo "=== [2/2] uvicorn backend.main:app -> http://${HOST}:${PORT} ==="
exec uv run uvicorn backend.main:app --host "$HOST" --port "$PORT" $RELOAD
