#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

export PATH="/tmp/node-v22.14.0-darwin-arm64/bin:$PATH"

echo "Building frontend..."
cd frontend
VITE_API=http://localhost:8000 node node_modules/.bin/vite build --logLevel silent
cd ..

echo "Starting server on :8000 (backend + frontend)..."
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
