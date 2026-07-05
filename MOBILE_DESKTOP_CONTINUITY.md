# MOBILE_DESKTOP_CONTINUITY.md — PC ⇄ Mobile ⇄ Desktop

## Current state (verified)

- Web: responsive Quasar SPA; `offline-queue.ts` (localStorage), `background-sync.ts` (interval), `platform.ts` — all with vitest coverage.
- Mobile: Capacitor config + `runtime-policy.ts` (+ test) + validators; no native project in archive; no share-target.
- Desktop: Tauri 2 config with CSP + validator; boilerplate Rust only.
- Backend: sync-engine with vector clocks, `mobile_offline_mutations` and `client_sync_state` tables, device identity + pairing codes (pairing not enforced), MinIO attachments.
- E2E: `offline-conflicts.spec.ts` exists.

## Continuity model

One rule: **every mutating action is queue-first on every platform.** The UI writes to the local queue and renders optimistically; a sync worker drains the queue with per-entity ordering; the server resolves with the existing vector-clock machinery; conflicts surface in `/continuity`.

### Offline queue v2 (closes R-08)

- Storage: localforage/IndexedDB (`boot/localdb.ts` already configures localforage — use it).
- Record: `{id, entity_kind, entity_id, device_seq, vector_hint, url, method, body, createdAt, attempts, status, lastError}`.
- Ordering: FIFO **per entity_id** (parallel across entities); `device_seq` monotonic per device feeds the vector clock.
- Backoff: exponential + jitter, cap 5 min;永 retry on 5xx/network, dead-letter on 4xx with an Attention chip.
- Size policy: 50 MB budget; attachments stored as blobs in IndexedDB, uploaded to MinIO first, body then references the object key.
- Privacy: optional at-rest encryption (WebCrypto AES-GCM, key in platform secure storage via Capacitor SecureStorage / Tauri stronghold; documented as best-effort on plain web).

### Background sync policy

- Web/desktop: interval (existing) + `online` event + visibility change.
- Mobile: Capacitor App state change + (Android) WorkManager periodic task via community background-runner plugin; policy object `{wifi_only?: bool, min_battery?: %, max_payload_mb}` stored in settings and honored by the drain worker.
- Every drain writes `client_sync_state` heartbeat → Continuity surface shows per-device "last seen / lag".

## Platform-specific capabilities

### Mobile (capture-first)
1. **Android share-target**: intent-filter for text/URL/image → opens Capture pre-filled → queue-first save. This single feature is the biggest daily-use unlock.
2. Quick-capture tile / app shortcut (long-press icon → "Capture", "New task").
3. Voice capture: record locally (Capacitor voice/media plugin), enqueue audio blob; transcription happens server-side when model-runtime has whisper configured; until then the item holds the audio with an honest `transcription: unavailable (no model)` state.
4. Camera/screenshot attach → MinIO attachments path (exists) + OCR via model-runtime heuristic (exists) with degraded label.
5. Pairing: first-run scans QR from desktop `/continuity` (pairing_codes table exists — enforce it in register when `AUTH_REQUIRED=true`).

### Desktop (Tauri)
1. Global shortcut `Ctrl+Shift+Space` → frameless quick-capture window (tauri-plugin-global-shortcut + secondary window).
2. Tray icon: badge = pending approvals + conflicts; menu: Capture, Approvals, Sync now, Open vault.
3. Scoped FS capability for the Obsidian vault path only (Tauri capability config) so vault sync can run client-side when the server is remote — v2; v1 keeps vault sync server-side.
4. Autostart (optional, off by default) + single-instance.

### Web
Keyboard-first (palette spec), PWA manifest + service worker for installability and capture-while-offline.

## Sync/backup health UX (Settings + Continuity)

Plain-language panel, all live:
- "This device last synced 2 min ago (3 items queued)."
- "Phone 'Pixel' last seen 4 h ago."
- "2 conflicts need your decision → Resolve."
- "Last backup 11 h ago, verified ✓; remote copy 1 d ago."
Every sentence maps to one endpoint; no synthetic scores.

## Test plan

- Unit: queue ordering per entity, backoff, dead-letter, policy gating (wifi_only), encryption round-trip.
- Playwright: extend `offline-conflicts.spec.ts` — go offline, create + edit same task on two "devices", reconnect, resolve conflict in UI.
- Device lane (marked `device`): Android share-target intent test, background drain smoke.
- Contract: register requires pairing code when AUTH_REQUIRED=true.
