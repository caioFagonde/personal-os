#!/usr/bin/env bash
set -euo pipefail
# Defensive local scan. This is not a substitute for provider-side secret scanning.
PATTERN='(AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9_]{20,}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|password\s*=\s*[^<\s][^\s]+|api[_-]?key\s*=\s*[^<\s][^\s]+)'
# .agents/.agentops/.agent-worktrees are untracked local agent telemetry (gitignored,
# never packaged — `make package` uses git archive). Their reports quote scanner
# phrases like "password=" in prose, which are false positives by construction.
EXCLUDES='--exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=.quasar --exclude-dir=__pycache__ --exclude-dir=.agents --exclude-dir=.agentops --exclude-dir=.agent-worktrees --exclude=.env.example --exclude=check-secrets.sh --exclude=pnpm-lock.yaml'
if grep -RInE $EXCLUDES "$PATTERN" .; then
  echo "Potential secret detected. Move it to .env/local secret store, rotate it, then retry." >&2
  exit 1
fi

# Personal-data scan (Phase A / risk R-01): no real email addresses or phone numbers
# may ship in source. Placeholders like user@example.com / example.org are allowed.
# Source dirs only: runtime data/, backups/, logs/ are already out of scope for commits.
PII_DIRS=(services apps packages modules scripts infra e2e tests docs)
EMAIL_PATTERN='[A-Za-z0-9._%+-]+@(gmail|outlook|hotmail|yahoo|proton|icloud|live)\.[A-Za-z]{2,}'
PHONE_PATTERN='\+[0-9]{10,15}'
PII_EXCLUDES='--exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.quasar --exclude-dir=__pycache__ --exclude=check-secrets.sh'
FOUND=0
if grep -RInE $PII_EXCLUDES "$EMAIL_PATTERN" "${PII_DIRS[@]}" 2>/dev/null; then
  FOUND=1
fi
if grep -RInE $PII_EXCLUDES "$PHONE_PATTERN" "${PII_DIRS[@]}" 2>/dev/null | grep -vE '(\+5511999999999|\+14155238886|\+1234567890|\+15551234567)'; then
  FOUND=1
fi
if [ "$FOUND" -ne 0 ]; then
  echo "Personal data (email/phone) detected in source. Move it to .env; never commit real contact details." >&2
  exit 1
fi
echo "No obvious secrets or personal data detected by local regex scan."
