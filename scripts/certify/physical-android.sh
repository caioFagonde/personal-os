#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

API_PORT="${API_GATEWAY_PORT:-8080}"
WEB_PORT="${WEB_PORT:-9000}"
WAIT_SECONDS="${ADB_WAIT_SECONDS:-300}"

echo "Checking adb availability..."
command -v adb >/dev/null 2>&1 || { echo "adb not found. Install Android platform-tools." >&2; exit 2; }

echo "Waiting for an authorized USB device. Accept the RSA prompt on the phone if it appears."
deadline=$((SECONDS + WAIT_SECONDS))
while (( SECONDS < deadline )); do
  adb start-server >/dev/null
  if adb devices | awk 'NR>1 && $2=="device" {found=1} END{exit !found}'; then
    break
  fi
  adb devices
  sleep 3
done
adb devices | awk 'NR>1 && $2=="device" {found=1} END{exit !found}' || { echo "No authorized adb device found." >&2; exit 3; }

DEVICE_ID="$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')"
echo "Authorized device: $DEVICE_ID"

# Let the phone reach PC localhost through USB for local certification.
adb reverse tcp:"$API_PORT" tcp:"$API_PORT" || true
adb reverse tcp:"$WEB_PORT" tcp:"$WEB_PORT" || true

if command -v pnpm >/dev/null 2>&1; then
  pnpm install --frozen-lockfile=false
  pnpm --dir apps/mobile validate
  pnpm --dir apps/mobile cap:add:android
  pnpm --dir apps/mobile cap:sync
  (cd apps/mobile/android && ./gradlew assembleDebug)
  APK="$(find apps/mobile/android/app/build/outputs/apk/debug -name '*.apk' | head -1)"
  [[ -n "$APK" ]] || { echo "Debug APK not found" >&2; exit 4; }
  adb install -r "$APK"
  echo "Installed $APK on $DEVICE_ID"
else
  echo "pnpm unavailable; cannot build mobile app." >&2
  exit 5
fi
