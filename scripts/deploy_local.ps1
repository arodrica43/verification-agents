# Local one-command deploy (development profile).
# Full stack: postgres, minio, redis, proof, certificate, retrieval, api, web.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:Path = "C:\Program Files\Docker\Docker\resources\bin;C:\Program Files\Docker\Docker\resources\cli-plugins;$env:Path"

if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host "Created .env from .env.example"
}

Write-Host "Waiting for Docker engine..."
$deadline = (Get-Date).AddMinutes(5)
do {
  docker info 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { break }
  Start-Sleep -Seconds 3
  if ((Get-Date) -gt $deadline) { throw "Docker engine did not become ready in time. Open Docker Desktop and retry." }
} while ($true)

Write-Host "Building and starting stack..."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw "docker compose failed" }

Write-Host "Waiting for API /ready..."
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8000/ready" -TimeoutSec 5
    if ($ready.status -eq "ready") { $ok = $true; break }
  } catch { Start-Sleep -Seconds 5 }
}
if (-not $ok) { throw "API did not become ready" }

python scripts/smoke_system.py --base-url http://127.0.0.1:8000
Write-Host ""
Write-Host "Deployed:"
Write-Host "  Studio  http://localhost:3000"
Write-Host "  API     http://localhost:8000/docs"
Write-Host "  Proof   http://localhost:8001/health"
