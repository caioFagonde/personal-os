$cmds = "git","docker","node","pnpm","python","adb","tailscale"
foreach ($c in $cmds) {
  if (Get-Command $c -ErrorAction SilentlyContinue) { Write-Host "✓ $c" } else { Write-Host "✗ $c missing" }
}
docker compose --env-file .env ps
