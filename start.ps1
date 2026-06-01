#!/usr/bin/env pwsh
param(
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$Reload,
    [switch]$BuildFrontend
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "=== [1/2] uv sync (Python deps) ==="
uv sync

if ($BuildFrontend) {
    Write-Host "=== (opt-in) build frontend -> frontend/dist (served on the same port) ==="
    Push-Location frontend
    try {
        if (-not (Test-Path node_modules)) { npm install }
        $env:VITE_API = "http://localhost:$Port"
        npm run build
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path "backend\.env")) {
    Write-Warning "backend/.env not found - copy backend/.env.example and fill the required keys, or boot fails fast."
}

Write-Host ("=== [2/2] uvicorn backend.main:app -> http://{0}:{1} ===" -f $BindHost, $Port)
$uvicornArgs = @("run", "uvicorn", "backend.main:app", "--host", $BindHost, "--port", "$Port")
if ($Reload) { $uvicornArgs += "--reload" }
& uv @uvicornArgs
exit $LASTEXITCODE
