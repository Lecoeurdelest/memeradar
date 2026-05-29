#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Building frontend (always fresh dist) ==="
Push-Location frontend
try {
    if (-not (Test-Path node_modules)) { npm install }
    $env:VITE_API = "http://localhost:8000"
    npm run build
} finally {
    Pop-Location
}

Write-Host "=== Starting server on http://localhost:8000 (backend + frontend) ==="
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
