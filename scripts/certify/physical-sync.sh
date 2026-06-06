#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
: "${ADB_WAIT_SECONDS:=300}"
: "${MOBILE_API_PORT:=8080}"
: "${MOBILE_WEB_PORT:=9000}"

if ! command -v adb >/dev/null 2>&1; then
  echo "adb is required. Install Android platform-tools." >&2
  exit 2
fi
adb start-server >/dev/null
end=$((SECONDS + ADB_WAIT_SECONDS))
while (( SECONDS < end )); do
  state="$(adb get-state 2>/dev/null || true)"
  if [[ "$state" == "device" ]]; then break; fi
  echo "Waiting for USB Android authorization. Unlock phone and accept the RSA prompt if shown..."
  adb devices || true
  sleep 5
done
[[ "$(adb get-state 2>/dev/null || true)" == "device" ]] || { echo "No authorized Android device detected." >&2; exit 1; }

adb reverse tcp:${MOBILE_API_PORT} tcp:${MOBILE_API_PORT} || true
adb reverse tcp:${MOBILE_WEB_PORT} tcp:${MOBILE_WEB_PORT} || true
pnpm install --frozen-lockfile=false
pnpm --dir apps/mobile validate
pnpm --dir apps/mobile cap:sync
pnpm --dir apps/mobile android:debug || ./scripts/deploy-android.sh
python3 scripts/certify/wait-http.py http://127.0.0.1:${MOBILE_API_PORT}/health 120
curl -fsS -X POST http://127.0.0.1:${MOBILE_API_PORT}/api/devices/register \
  -H 'content-type: application/json' \
  -d '{"device_key":"physical-android-cert","name":"Physical Android Certification","kind":"mobile","platform":"android"}' >/tmp/personal-os-phone-token.json
python3 - <<'PY'
import json
p=json.load(open('/tmp/personal-os-phone-token.json'))
assert p.get('access_token') and p.get('refresh_token')
print('physical Android device registration path certified')
PY
