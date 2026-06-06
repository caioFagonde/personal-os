$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Need($cmd) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "$cmd is required" }
}

Need git
Need docker
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  python scripts/generate-env.py .env
}
New-Item -ItemType Directory -Force data,logs,tmp,cache,artifacts,exports,generated,workspace | Out-Null
docker compose --env-file .env --profile core up -d --build
Write-Host "Personal OS core started. API: http://localhost:8080"
