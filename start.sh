#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

export PATH="/tmp/node-v22.14.0-darwin-arm64/bin:$PATH"

echo "Starting backend on :8000 ..."
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Building frontend..."
cd frontend
VITE_API=http://localhost:8000 node node_modules/.bin/vite build --logLevel silent

echo "Starting frontend on :5173 ..."
node node_modules/.bin/vite preview --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
