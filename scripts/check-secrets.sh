#!/usr/bin/env bash
set -euo pipefail
# Defensive local scan. This is not a substitute for provider-side secret scanning.
PATTERN='(AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9_]{20,}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|password\s*=\s*[^<\s][^\s]+|api[_-]?key\s*=\s*[^<\s][^\s]+)'
EXCLUDES='--exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude=.env.example --exclude=check-secrets.sh'
if grep -RInE $EXCLUDES "$PATTERN" .; then
  echo "Potential secret detected. Move it to .env/local secret store, rotate it, then retry." >&2
  exit 1
fi
echo "No obvious secrets detected by local regex scan."
