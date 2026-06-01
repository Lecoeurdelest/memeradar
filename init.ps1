#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

Write-Host "=== uv sync (Python deps) ==="
uv sync

Write-Host "=== npm install (frontend deps) ==="
Push-Location frontend
try {
    if (-not (Test-Path node_modules)) { npm install } else { Write-Host "node_modules present, skipping" }
    if (-not (Test-Path .env)) { "VITE_API=http://localhost:8000" | Out-File -Encoding ascii .env }
} finally {
    Pop-Location
}

Write-Host "=== backend import smoke ==="
uv run python -c "import backend.main; print('backend.main OK')"

Write-Host "=== datastore probes (non-fatal) ==="
function Probe($name, $url) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri $url
        Write-Host ("  {0}: UP ({1})" -f $name, $r.StatusCode)
    } catch {
        Write-Warning ("  {0}: DOWN at {1}" -f $name, $url)
    }
}
Probe "qdrant" "http://localhost:6333/healthz"
Probe "neo4j"  "http://localhost:7474"

Write-Host "=== required env vars ==="
$envFile = "backend\.env"
if (Test-Path $envFile) {
    $required = @("TL_API_KEY","MISTRAL_API_KEY","NEO4J_PASSWORD","REDDIT_CLIENT_ID","REDDIT_CLIENT_SECRET")
    $missing = @()
    $content = Get-Content $envFile -Raw
    foreach ($k in $required) {
        if ($content -notmatch "(?m)^\s*$k\s*=\s*\S") { $missing += $k }
    }
    if ($missing.Count -gt 0) {
        Write-Warning ("missing/empty in backend/.env: {0}" -f ($missing -join ", "))
    } else {
        Write-Host "  all required keys present"
    }
} else {
    Write-Warning "backend/.env not found; copy backend/.env.example"
}

Write-Host "=== init complete ==="
Write-Host "Start backend (single command):"
Write-Host "  ./start.ps1                 # uv sync + uvicorn on :8000"
Write-Host "Optional dev UI:"
Write-Host "  cd frontend; npm run dev"
