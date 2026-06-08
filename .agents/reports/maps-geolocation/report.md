# Report: maps-geolocation

## Summary

Implemented browser Geolocation API integration, permission-denied manual fallback, coordinate validation (client + server), tile-server availability detection with setup instructions, and AR capability state reporting for orientation/geolocation/motion.

## Files changed

| File | Change |
|------|--------|
| `apps/web/src/pages/GeospatialPage.vue` | Added "Use current location" button using `navigator.geolocation.getCurrentPosition`; permission-denied/unsupported banners with manual fallback; client-side lat/lng validation (-90..90, -180..180); tile-server availability check via `/api/geospatial/map-datasets` with setup flow banner |
| `apps/web/src/pages/ARMemoryPage.vue` | Added device capabilities card showing geolocation, orientation (DeviceOrientationEvent), and motion (DeviceMotionEvent) states as colored chips; detects granted/denied/unsupported via Permissions API and feature detection |
| `services/module-service/app/main.py` | Added `ge`/`le` validation to `GeoMemoryIn.latitude` (-90..90), `GeoMemoryIn.longitude` (-180..180), `RoutePlanRequest` coordinates, and `nearby` query params |
| `scripts/certify/maps-smoke.sh` | New smoke test verifying all acceptance criteria via grep checks |

## Tests run and results

| Test | Result |
|------|--------|
| `bash -n scripts/certify/maps-smoke.sh` | Syntax OK |
| `bash scripts/certify/maps-smoke.sh` | 17/17 checks passed |
| `python3 -m pytest services/module-service/tests/ -q` (from service dir) | 5/5 passed |

## Acceptance status

| Criterion | Status |
|-----------|--------|
| Use current location button uses browser Geolocation API | Done |
| Permission denied shows manual fallback | Done |
| Coordinates validated | Done (client + server) |
| TileServer/map-data missing shows setup flow | Done |
| AR page shows orientation/geolocation capability states honestly | Done |

## Remaining risks

- Tile-server detection checks the `map-datasets` API endpoint, not the actual tile-server HTTP health. If the module-service is down but tileserver is up, the banner will show incorrectly. Acceptable for now since there's no separate tileserver URL configured.
- iOS 13+ requires explicit `DeviceOrientationEvent.requestPermission()` user gesture — current code detects the API exists but the actual permission grant needs a button tap. A follow-up could add a "Request sensor access" button for iOS Safari.
- The Permissions API for geolocation state is not available in all browsers; fallback treats `prompt` state as `available` which is the correct default.

## Suggested follow-up tasks

- Add a Leaflet/MapLibre map view to GeospatialPage showing memories as markers on tiles (requires tileserver integration).
- Add iOS DeviceOrientationEvent.requestPermission() button on AR page for Safari.
- Add live orientation readout on AR page when sensors are available.
- Add E2E Playwright test for geolocation flow using geolocation mock.
