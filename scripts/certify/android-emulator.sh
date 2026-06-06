#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

command -v adb >/dev/null 2>&1 || { echo "adb not found." >&2; exit 2; }
command -v pnpm >/dev/null 2>&1 || { echo "pnpm not found." >&2; exit 2; }

adb wait-for-device
adb reverse tcp:${API_GATEWAY_PORT:-8080} tcp:${API_GATEWAY_PORT:-8080} || true
adb reverse tcp:${WEB_PORT:-9000} tcp:${WEB_PORT:-9000} || true
pnpm install --frozen-lockfile=false
pnpm --dir apps/mobile validate
pnpm --dir apps/mobile cap:add:android
pnpm --dir apps/mobile cap:sync
(cd apps/mobile/android && ./gradlew assembleDebug)
APK="$(find apps/mobile/android/app/build/outputs/apk/debug -name '*.apk' | head -1)"
adb install -r "$APK"
adb shell am start -n io.personalos.mobile/.MainActivity || true
adb logcat -d | tail -200 > artifacts/android-emulator-logcat.txt || true
