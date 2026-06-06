# Phase 7 — Production hardening and premium UX

Phase 7 turns the scaffold from a working modular substrate into a release-oriented product foundation.

## Backend hardening

- Service-to-service HMAC identity tokens with bounded TTL and explicit internal scopes.
- In-process RED metrics for the API gateway exposed at `/metrics`.
- Release metadata endpoint at `/api/release`.
- PostgreSQL migration for service identities, durable consumers, release channels, client sync state, UX preferences, telemetry events, and service health snapshots.
- Observability Compose profile now includes OpenTelemetry Collector, Prometheus, Grafana dashboards, and Loki.

## UX/UI system

- Premium shell layout with responsive desktop drawer and mobile bottom navigation.
- Command palette on `Ctrl/⌘ K`.
- Glass-panel visual language, fluid type scale, accessibility contrast helpers, and reduced-motion support.
- Shared `@personal-os/design-system` package.
- Mobile-safe area handling and platform-adaptive density.

## Mobile

- Runtime policy for background sync budgeting based on network, battery, charging state, and pending mutation count.
- Capacitor preflight script validates mesh navigation and notification configuration.
- Mobile tests cover background-sync policy.

## Desktop

- Tauri shell exposes native health, runtime context, and deep-link validation commands.
- Unsafe deep-link schemes are rejected.
- Desktop tests cover shell capabilities and link sanitization.

## Release automation

- `release.yml` builds web, Android project artifacts, and desktop bundles.
- `scripts/release/build-manifest.py` generates deterministic SHA-256 release manifests.
- `release_channels` table is ready for staged rollout metadata.

## Commands

```bash
make up-observability
make test-phase7
pnpm --dir packages/design-system test
pnpm --dir apps/mobile preflight
scripts/ops/collect-health.sh
```
