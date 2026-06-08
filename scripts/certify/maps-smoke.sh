#!/usr/bin/env bash
# maps-smoke.sh — quick checks for maps/geolocation pages
set -euo pipefail

FAIL=0
pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; FAIL=1; }

echo "=== Maps / Geolocation smoke ==="

# --- GeospatialPage.vue ---
GEO_PAGE="apps/web/src/pages/GeospatialPage.vue"
echo ""
echo "Checking $GEO_PAGE ..."

if [ ! -f "$GEO_PAGE" ]; then
  fail "File missing: $GEO_PAGE"
else
  # Geolocation API usage
  grep -q 'navigator.geolocation' "$GEO_PAGE" && pass "Uses browser Geolocation API" || fail "Missing navigator.geolocation"

  # getCurrentPosition call
  grep -q 'getCurrentPosition' "$GEO_PAGE" && pass "Calls getCurrentPosition" || fail "Missing getCurrentPosition"

  # Permission denied handling
  grep -q 'PERMISSION_DENIED' "$GEO_PAGE" && pass "Handles PERMISSION_DENIED" || fail "Missing PERMISSION_DENIED handling"

  # Manual fallback visible on denied
  grep -q "geoState === 'denied'" "$GEO_PAGE" && pass "Shows manual fallback on denied" || fail "Missing denied fallback UI"

  # Coordinate validation
  grep -q 'isValidLat' "$GEO_PAGE" && pass "Client-side lat validation" || fail "Missing lat validation"
  grep -q 'isValidLng' "$GEO_PAGE" && pass "Client-side lng validation" || fail "Missing lng validation"

  # Tile server check
  grep -q 'tileStatus' "$GEO_PAGE" && pass "Tile server availability check" || fail "Missing tile server check"
  grep -q 'map-datasets' "$GEO_PAGE" && pass "Queries map-datasets endpoint" || fail "Missing map-datasets query"
fi

# --- ARMemoryPage.vue ---
AR_PAGE="apps/web/src/pages/ARMemoryPage.vue"
echo ""
echo "Checking $AR_PAGE ..."

if [ ! -f "$AR_PAGE" ]; then
  fail "File missing: $AR_PAGE"
else
  # Geolocation capability detection
  grep -q 'geoCap' "$AR_PAGE" && pass "Geolocation capability state" || fail "Missing geoCap state"

  # Orientation capability detection
  grep -q 'orientationCap' "$AR_PAGE" && pass "Orientation capability state" || fail "Missing orientationCap state"

  # Motion capability detection
  grep -q 'motionCap' "$AR_PAGE" && pass "Motion capability state" || fail "Missing motionCap state"

  # DeviceOrientationEvent check
  grep -q 'DeviceOrientationEvent' "$AR_PAGE" && pass "Checks DeviceOrientationEvent" || fail "Missing DeviceOrientationEvent check"

  # Shows denied/unsupported states
  grep -q "denied" "$AR_PAGE" && pass "Shows denied state" || fail "Missing denied state UI"
  grep -q "unsupported" "$AR_PAGE" && pass "Shows unsupported state" || fail "Missing unsupported state UI"
fi

# --- Server-side validation ---
MODULE_MAIN="services/module-service/app/main.py"
echo ""
echo "Checking $MODULE_MAIN ..."

if [ ! -f "$MODULE_MAIN" ]; then
  fail "File missing: $MODULE_MAIN"
else
  grep -q 'ge=-90, le=90' "$MODULE_MAIN" && pass "Server-side lat validation" || fail "Missing server lat validation"
  grep -q 'ge=-180, le=180' "$MODULE_MAIN" && pass "Server-side lng validation" || fail "Missing server lng validation"
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "ALL CHECKS PASSED"
else
  echo "SOME CHECKS FAILED"
  exit 1
fi
