#!/usr/bin/env bash
set -euo pipefail

echo "=== uv sync (Python deps) ==="
uv sync

echo "=== npm install (frontend deps) ==="
(
  cd frontend
  if [ ! -d node_modules ]; then npm install; else echo "node_modules present, skipping"; fi
  if [ ! -f .env ]; then echo "VITE_API=http://localhost:8000" > .env; fi
)

echo "=== backend import smoke ==="
uv run python -c "import backend.main; print('backend.main OK')"

echo "=== datastore probes (non-fatal) ==="
probe() {
  local name=$1 url=$2
  if curl -fsS -m 2 -o /dev/null "$url"; then
    echo "  $name: UP"
  else
    echo "  $name: DOWN at $url" >&2
  fi
}
probe qdrant http://localhost:6333/healthz
probe neo4j  http://localhost:7474

echo "=== required env vars ==="
envfile=backend/.env
if [ -f "$envfile" ]; then
  required=(TL_API_KEY MISTRAL_API_KEY NEO4J_PASSWORD REDDIT_CLIENT_ID REDDIT_CLIENT_SECRET)
  missing=()
  for k in "${required[@]}"; do
    if ! grep -Eq "^[[:space:]]*${k}[[:space:]]*=[[:space:]]*[^[:space:]]" "$envfile"; then
      missing+=("$k")
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "  missing/empty in backend/.env: ${missing[*]}" >&2
  else
    echo "  all required keys present"
  fi
else
  echo "  backend/.env not found; copy backend/.env.example" >&2
fi

echo "=== init complete ==="
echo "Start backend (single command):"
echo "  ./start.sh                   # uv sync + uvicorn on :8000"
echo "Optional dev UI:"
echo "  (cd frontend && npm run dev)"
