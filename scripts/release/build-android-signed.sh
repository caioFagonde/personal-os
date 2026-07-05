#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

OUT_DIR="artifacts/release/android"
mkdir -p "$OUT_DIR"

command -v pnpm >/dev/null 2>&1 || { echo "pnpm is required" >&2; exit 2; }
command -v base64 >/dev/null 2>&1 || { echo "base64 is required" >&2; exit 2; }

pnpm install --frozen-lockfile=false
pnpm --dir apps/mobile validate
pnpm --dir apps/mobile cap:add:android
pnpm --dir apps/mobile cap:sync

if [[ -z "${ANDROID_KEYSTORE_BASE64:-}" || -z "${ANDROID_KEY_ALIAS:-}" || -z "${ANDROID_KEYSTORE_PASSWORD:-}" || -z "${ANDROID_KEY_PASSWORD:-}" ]]; then
  echo "Android signing secrets not present. Building unsigned release project artifact."
  (cd apps/mobile/android && ./gradlew assembleRelease)
  find apps/mobile/android/app/build/outputs -type f \( -name '*.apk' -o -name '*.aab' \) -exec cp {} "$OUT_DIR" \;
  exit 0
fi

KEYSTORE="apps/mobile/android/personal-os-release.jks"
echo "$ANDROID_KEYSTORE_BASE64" | base64 -d > "$KEYSTORE"
(cd apps/mobile/android && ./gradlew assembleRelease)
UNSIGNED_APK="$(find apps/mobile/android/app/build/outputs/apk/release -name '*release*.apk' | head -1)"
[[ -n "$UNSIGNED_APK" ]] || { echo "Release APK not found" >&2; exit 3; }

ZIPALIGN="${ANDROID_HOME:-$ANDROID_SDK_ROOT}/build-tools/${ANDROID_BUILD_TOOLS_VERSION:-35.0.0}/zipalign"
APKSIGNER="${ANDROID_HOME:-$ANDROID_SDK_ROOT}/build-tools/${ANDROID_BUILD_TOOLS_VERSION:-35.0.0}/apksigner"
if [[ ! -x "$ZIPALIGN" || ! -x "$APKSIGNER" ]]; then
  ZIPALIGN="$(find "${ANDROID_HOME:-$ANDROID_SDK_ROOT}/build-tools" -name zipalign | sort -V | tail -1)"
  APKSIGNER="$(find "${ANDROID_HOME:-$ANDROID_SDK_ROOT}/build-tools" -name apksigner | sort -V | tail -1)"
fi

ALIGNED="$OUT_DIR/personal-os-release-aligned.apk"
SIGNED="$OUT_DIR/personal-os-release-signed.apk"
"$ZIPALIGN" -f -p 4 "$UNSIGNED_APK" "$ALIGNED"
"$APKSIGNER" sign \
  --ks "$KEYSTORE" \
  --ks-key-alias "$ANDROID_KEY_ALIAS" \
  --ks-pass "pass:$ANDROID_KEYSTORE_PASSWORD" \
  --key-pass "pass:$ANDROID_KEY_PASSWORD" \
  --out "$SIGNED" \
  "$ALIGNED"
"$APKSIGNER" verify --verbose "$SIGNED"
sha256sum "$SIGNED" > "$SIGNED.sha256"
echo "Signed APK: $SIGNED"
