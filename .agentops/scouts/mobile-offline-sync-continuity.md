# Scout Report: Mobile Offline Queue and Sync Continuity UX

**Task:** mobile-offline-sync-continuity - Mobile offline queue and sync continuity UX
**Date:** 2026-06-08
**Status:** Ready for implementation

---

## Executive Summary

The offline queue infrastructure exists in partial form: a localStorage-backed mutation store (`offline-queue.ts`), background sync strategy (`background-sync.ts`), and UI page (`OfflineQueuePage.vue`). However, no mutation-creating page (Capture, Tasks, etc.) actually uses the queue, and there is no integration between offline mutations and the sync push/pull endpoints. The SystemStatusRibbon shows sync status but does not track real pending mutations. Mobile-first UX for offline continuity is incomplete.

**Gap:** Pages make direct API calls with no fallback to offline queue on network failure. Users lose mutations on network drops.

---

## Relevant Files

### Core Offline Queue Infrastructure

- `apps/web/src/services/offline-queue.ts` — localStorage-backed mutation queue with enqueue/load/clear operations
- `apps/web/src/services/offline-queue.test.ts` — tests for queue helpers (load, enqueue, clear)
- `apps/web/src/services/background-sync.ts` — strategy for deciding when to sync (online, battery, mutation count, staleness)
- `apps/web/src/services/background-sync.test.ts` — tests for background sync decisioning
- `apps/web/src/services/api.ts` — jsonFetch and uploadFile helpers (no offline interception)
- `apps/web/src/services/platform.ts` — platform detection (mobile/desktop/web) and layout preferences
- `apps/web/src/services/auth.ts` — device key and token management

### UI Pages and Components

- `apps/web/src/pages/OfflineQueuePage.vue` — displays queue items, status, attempts, error messages
- `apps/web/src/pages/ConflictResolutionPage.vue` — conflict UI (integrates with sync-engine `/api/sync/conflicts`)
- `apps/web/src/pages/SyncPage.vue` — sync dashboard showing health, open conflicts, round-trip testing
- `apps/web/src/pages/SyncHealthPage.vue` — control-plane health checks
- `apps/web/src/pages/CapturePage.vue` — quick capture (POST to captureUrl; no offline queueing)
- `apps/web/src/pages/TasksPage.vue` — task management (POST/GET to captureUrl; no offline queueing)
- `apps/web/src/components/SystemStatusRibbon.vue` — shows online/offline, pending count, conflict count (NOT tracking real queue)
- `apps/web/src/components/BottomNav.vue` — mobile navigation (hardcoded modules, no offline queue link)

### Router and App Shell

- `apps/web/src/router/routes.ts` — `/offline-queue` and `/conflicts` routes registered
- `apps/web/src/App.vue` — tracks `online` with window events, but `pendingMutations` is hardcoded to 0
- `apps/web/src/components/BottomNav.vue` — mobile footer with 5 routes (no link to offline queue)

### Mobile App

- `apps/mobile/` — Capacitor wrapper; web output lives at `../web/dist/spa`
- `apps/mobile/capacitor.config.ts` — references web build; allows localhost and *.ts.net (Tailscale)

### Backend Services

- `services/sync-engine/app/main.py` — push/pull endpoints, conflict detection, health endpoint
- `services/api-gateway/app/main.py` — proxies requests to services, handles auth, no offline queue endpoint
- `services/capture-service/app/main.py` — capture and task creation (no batch replay from offline queue)

### Migrations and Schema

- `infra/postgres/migrations/` — sync_log, sync_conflicts, entities, entity_versions tables exist
- `packages/schemas/src/sync.ts` — SyncChange, SyncPullResponse interfaces

### Tests and E2E

- `e2e/offline-conflicts.spec.ts` — expects `/offline-queue` route to show queue UI and accept test mutation
- `tests/test_phase11_scaffold.py` — validates offline-queue page, conflicts page, and connector-worker routes exist
- `apps/web/src/services/*.test.ts` — unit tests for offline-queue and background-sync (not integration tests)

### Documentation

- `docs/sync-protocol.md` — describes append-only sync, push/pull, merge strategies, conflict handling
- `docs/phase-11-production-continuity.md` — lists implemented UX (offline queue, conflict resolution, device pairing)

---

## Current State Assessment

### What Works

1. **Offline queue data layer**: `enqueueOfflineMutation()`, `loadOfflineQueue()`, `saveOfflineQueue()` properly store/retrieve from localStorage with error recovery.
2. **Background sync strategy**: Decision logic for when to sync based on network, battery, queue size, and staleness.
3. **Offline queue UI**: OfflineQueuePage displays queue items with status, method, URL, attempts, and body; test button creates smoke mutations.
4. **System status banner**: SystemStatusRibbon displays online/offline and hints about sync health.
5. **Conflict resolution UI**: ConflictResolutionPage allows manual resolution of conflicts from sync-engine.
6. **Sync health dashboard**: SyncPage shows health metrics, open conflicts, and can trigger round-trip tests.
7. **Router integration**: Both `/offline-queue` and `/conflicts` routes are registered.
8. **Platform detection**: Mobile vs. desktop layout branching is implemented.
9. **Sync endpoints on backend**: sync-engine push/pull/conflicts endpoints exist and are tested.

### What's Missing

1. **No offline interception in API calls**: CapturePage, TasksPage, and other pages make direct calls to `jsonFetch()` with no try-catch to queue on failure.
2. **No real-time mutation tracking**: App.vue hardcodes `pendingMutations` to 0; it never reads from the offline queue.
3. **No sync trigger**: Background-sync strategy exists, but there's no scheduler or interval listener to actually call sync when conditions are met.
4. **No batch sync endpoint**: API gateway has no `/api/queue/sync` or similar to replay queued mutations.
5. **No offline state indicator on mutation-creating pages**: Capture and Tasks pages don't indicate if operations will be queued vs. sent immediately.
6. **No retry logic**: Queued mutations have `attempts` field but no code to increment it or backoff.
7. **No duplicate prevention**: If a user taps "capture" twice while offline, two identical mutations are queued.
8. **No optimistic UI updates**: Pages don't show queued mutations as "pending" until sync.
9. **No mobile-first offline queue UX**: BottomNav doesn't link to offline queue; no collapsed badge on mobile to show pending count.
10. **No error context**: Failed mutations store a generic `error` string but not the response body or timestamp.
11. **No unobtrusive sync status on mobile**: Mobile users see the SystemStatusRibbon but it's not prominently placed.
12. **No integration tests**: No tests verify that a failed API call queues to offline queue and later syncs.
13. **No graceful degradation**: Pages show errors but don't offer to queue the operation for later.

---

## Implementation Points

### Frontend: User-Facing Offline Flow

**Phases:**

1. **Intercept failed API calls** (CapturePage, TasksPage, etc.)
   - Wrap `jsonFetch()` calls in try-catch for all mutation operations
   - On network error or offline, offer to queue: "Offline. Queue for later?"
   - Call `enqueueOfflineMutation()` with original request

2. **Track pending mutations in App.vue**
   - Create a Pinia store (or reactive ref) to hold loaded queue
   - Watch offline queue on mount and periodically refresh
   - Bind `pendingMutations` to `loadOfflineQueue().length`
   - Emit counts to SystemStatusRibbon

3. **Add sync trigger**
   - Listen to `online` event; auto-sync when network returns
   - OR add a manual "Sync now" button visible on mobile when mutations pending
   - Call backend `/api/queue/sync` or `/api/sync/push` with queued mutations

4. **Enhance OfflineQueuePage**
   - Show retry count per mutation
   - Show error reason if available
   - Add "Retry all" or "Delete" per mutation
   - Show last sync time and next scheduled sync

5. **Mobile-first UX**
   - Add offline queue badge to BottomNav when count > 0
   - Show inline "Offline — changes saved locally" banner on CapturePage/TasksPage
   - Add "Sync now" button to SystemStatusRibbon when pending mutations > 0
   - Safe-area padding adjustments if status banner grows

### Backend: Offline Queue Replay

**Scope (if implemented by executor):**

1. **New endpoint**: `/api/queue/sync` (POST)
   - Accept list of offline mutations
   - Validate and deduplicate by `(url, body)` hash
   - Replay each mutation with appropriate HTTP method
   - Return per-mutation status (synced, conflict, failed)

2. **Idempotency**
   - Mutations should be idempotent (POST creates with `external_id`, UPDATE with `entity_id`)
   - Use `ON CONFLICT DO UPDATE` in captures and tasks if resubmitted

3. **Conflict handling**
   - If sync-engine detects conflict, surface it in UI
   - Link to ConflictResolutionPage

### Mobile-Specific Considerations

- Safe area padding: Use `safeAreaStyle()` from platform.ts
- Tap targets: Buttons on offline queue page ≥44px
- Network status: Capacitor can provide better network detection than window.onLine
- Battery awareness: Capacitor DeviceInfo API available for battery level
- Persistent storage: localStorage survives app close but not uninstall; consider IndexedDB or native storage for backup

---

## Risks and Conflicts

### Risk 1: Duplicate Mutations

**Scenario:** User captures a task offline, sees no confirmation, taps again, two mutations queue.
**Mitigation:** Deduplicate by mutation hash before sync. Show optimistic confirmation immediately on enqueue.

### Risk 2: Stale Mutations After Sync

**Scenario:** User queues 10 mutations. Network returns. 9 sync successfully. 1 fails due to validation. User doesn't notice the failed one.
**Mitigation:** Always show a summary banner after sync: "9/10 synced. 1 failed." Link to OfflineQueuePage.

### Risk 3: Conflict Explosion

**Scenario:** User works offline for hours, creates 50 note versions. Syncs. 10 conflicts appear. User overwhelmed.
**Mitigation:** Batch conflict UI with "Resolve all with remote" / "Resolve all with local" for same entity.

### Risk 4: Battery Drain

**Scenario:** Background sync runs every 60s, wakes CPU, drains battery.
**Mitigation:** Respect Capacitor battery API; don't sync if battery < 15% and not charging.

### Risk 5: Storage Quota

**Scenario:** User queues large image uploads offline. localStorage quota (5–10 MB per origin) exceeded.
**Mitigation:** Warn user if queue size > 1 MB. Prioritize small mutations first. Docs should recommend Sync > Clear.

### Risk 6: API Changes Break Queue Replay

**Scenario:** Offline mutations reference old API shape. After update, queue fails to replay.
**Mitigation:** Schema version in mutations. Migration path in sync endpoint. Tests verify backward compat.

### Risk 7: Mobile Safe Area Collision

**Scenario:** StatusRibbon + BottomNav + soft keyboard overlap on small screens.
**Mitigation:** Test on iPhone SE (375px) and Android phone (375px). Adjust padding dynamically.

### Risk 8: Sync Engine Unavailable

**Scenario:** User offline for days, queues work, returns online, sync-engine is down.
**Mitigation:** Catch 5xx from sync endpoint. Offer to retry later. Don't auto-clear queue on 5xx.

---

## Tests to Run

### Unit Tests (Existing)

```bash
pnpm --dir apps/web test offline-queue.test.ts
pnpm --dir apps/web test background-sync.test.ts
```

### Integration Tests (To Add)

1. **Test offline queue + capture integration**
   - Mock network error on POST /api/proxy/capture
   - Verify mutation enqueued
   - Verify OfflineQueuePage displays it

2. **Test sync replay**
   - Queue mutations offline
   - Call `/api/queue/sync` backend endpoint
   - Verify mutations persisted in capture service
   - Verify offline queue cleared

3. **Test conflict detection**
   - Queue mutation to note that conflicts with remote
   - Sync
   - Verify conflict surfaced in ConflictResolutionPage

4. **Test retry logic**
   - Queue mutation
   - Mark as failed
   - Increment attempts
   - Verify exponential backoff

### E2E Tests (Existing + Enhance)

```bash
npx playwright test e2e/offline-conflicts.spec.ts
```

**Existing:**
- Offline queue page loads and displays mutations
- Conflict page shows merge controls

**To Add:**
- Offline: capture → queue
- Offline: create task → queue
- Online: sync queued mutations
- Offline: add mutation → online: sync → OfflineQueuePage shows synced status
- Mobile: offline queue accessible from mobile menu

### Manual Testing Checklist

- [ ] Capture offline: text input disabled or visually softened?
- [ ] Offline: "Queue this for later?" dialog appears on error
- [ ] SystemStatusRibbon shows pending count > 0
- [ ] OfflineQueuePage loads queued mutations
- [ ] Network returns: auto-sync or manual "Sync now" button?
- [ ] Sync completes: OfflineQueuePage shows synced status
- [ ] Partial sync failure: summary banner shows count
- [ ] Mobile BottomNav: does offline queue badge appear?
- [ ] Mobile: soft keyboard doesn't overlap status ribbon
- [ ] Conflict resolution: after resolution, sync resumes

---

## Files to Touch (Implementation Scope)

### Frontend Layer

**Modify (wrap API calls):**
- `apps/web/src/pages/CapturePage.vue` — wrap capture() in try-catch, queue on error
- `apps/web/src/pages/TasksPage.vue` — wrap createTask() and complete(), queue on error
- `apps/web/src/services/api.ts` — optional: wrap jsonFetch/uploadFile to auto-queue on 5xx/network error

**Create or Enhance:**
- `apps/web/src/stores/offline.ts` (new) — Pinia store to track queue state and expose isPending, syncNow()
- `apps/web/src/App.vue` — load offline queue on mount, bind pendingMutations to store, add sync trigger

**Enhance UI:**
- `apps/web/src/pages/OfflineQueuePage.vue` — add retry, delete, sync-now buttons; show error detail
- `apps/web/src/components/SystemStatusRibbon.vue` — link pending count to /offline-queue, add sync-now button
- `apps/web/src/components/BottomNav.vue` — add offline-queue to navigation with badge if pending > 0
- `apps/web/src/pages/CapturePage.vue` — show "offline" indicator or dialog when queueing

**Optional (better UX):**
- `apps/web/src/services/api.ts` — wrap jsonFetch to detect offline and queue (global error handler)
- `apps/web/src/composables/useOfflineQueue.ts` (new) — composable for pages to easily integrate offline queueing

### Backend Layer (If Executor Adds)

**Create:**
- `services/api-gateway/app/queue.py` (new) — `/api/queue/sync` endpoint to replay mutations
- `services/api-gateway/tests/test_queue_sync.py` (new) — tests for queue sync logic

**Modify:**
- `services/capture-service/app/main.py` — ensure POST /api/capture uses external_id for idempotency
- `services/api-gateway/app/main.py` — add queue sync route

### Tests

**Create:**
- `apps/web/src/pages/CapturePage.test.ts` — offline queueing integration test
- `apps/web/src/pages/TasksPage.test.ts` — offline queueing integration test
- `e2e/offline-queue-sync.spec.ts` — end-to-end sync replay test

**Modify:**
- `e2e/offline-conflicts.spec.ts` — enhance with sync replay scenario

### Documentation

**Update:**
- `docs/sync-protocol.md` — add offline queue replay section
- `docs/phase-11-production-continuity.md` — or create `phase-15-offline-continuity.md`

---

## Suggested Executor Instructions

### If Starting Implementation

1. **Create offline queue Pinia store** (5 min)
   - Load queue on app mount
   - Expose `pendingCount`, `isPending`, `syncNow()` action
   - Watch `online` event; auto-sync when network returns

2. **Enhance OfflineQueuePage** (15 min)
   - Add retry/delete/sync buttons per mutation
   - Show sync status (pending, syncing, synced, failed)
   - Link sync errors to troubleshooting docs

3. **Wrap CapturePage capture()** (10 min)
   - Try-catch POST to captureUrl
   - On error, show "Queue for later?" dialog
   - Call store.enqueueOfflineMutation() if confirmed

4. **Wrap TasksPage createTask()** (10 min)
   - Same pattern as CapturePage

5. **Update SystemStatusRibbon** (10 min)
   - Show pending count from store
   - Add sync-now button if pending > 0
   - Link to OfflineQueuePage

6. **Add mobile UI** (15 min)
   - Update BottomNav to show offline-queue if pending > 0
   - Adjust padding for status ribbon on mobile
   - Test on mobile viewport

7. **Backend queue sync endpoint** (20 min)
   - POST /api/queue/sync accepts list of mutations
   - Validates and deduplicates
   - Replays to original services
   - Returns per-mutation status

8. **Integration tests** (20 min)
   - Test offline capture → queue
   - Test sync → clear
   - Test conflict detection

**Estimated Total:** 1–2 hours frontend, 30 min backend, if starting from scratch.

---

## Acceptance Criteria Checklist

- [ ] Mobile-first offline queue UI exists (OfflineQueuePage enhanced with sync controls)
- [ ] Capture/tasks can queue offline mutations (CapturePage/TasksPage wrap jsonFetch with enqueue fallback)
- [ ] Sync state, retry state, conflict state, and pending count are visible (SystemStatusRibbon, OfflineQueuePage, mobile badge)
- [ ] No failed network call crashes the UI (error handling with graceful queue fallback)
- [ ] Empty states and setup actions exist (OfflineQueuePage empty state, "Sync now" button, "Queue for later?" dialog)
- [ ] Tests cover offline queue contracts (unit tests for store, integration tests for page queueing, e2e for sync)

---

## Key Unknowns

1. **Should sync auto-trigger on network return, or require manual button?** → Recommend: auto-sync with user confirmation for large queues.
2. **Should failed mutations be retried with exponential backoff, or require manual retry?** → Recommend: manual retry with "Retry all" button; exponential backoff in background optional.
3. **Should Capacitor battery/network APIs be used, or stick to standard Web APIs?** → Recommend: use Capacitor for mobile, fallback to Web APIs on web; this requires mobile-specific branch.
4. **Should queue survive app uninstall/reinstall?** → Recommend: document that localStorage is ephemeral; don't promise durability across reinstalls.
5. **How to handle very large queues (100+ mutations)?** → Recommend: paginate OfflineQueuePage, batch syncs in 10-mutation chunks, warn user if queue > 1 MB.

---

## Conclusion

The skeleton is in place: offline-queue service, UI page, and route. The implementation requires wiring API calls to use the queue as a fallback, tracking pending mutations in global state, adding a sync mechanism, and enhancing UX with mobile-friendly indicators and controls. No architectural blocker exists; this is a straightforward integration task with medium scope (2–4 hours for core offline capture/tasks flow, optional 1 hour for backend queue sync endpoint).

The main risk is duplicate mutations and sync failures; both are mitigated by deduplication, error tracking, and user-facing summaries.

