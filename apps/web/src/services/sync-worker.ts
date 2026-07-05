// Sync worker (Phase E1): drains the durable queue on a policy-gated cadence
// and posts a heartbeat to the server so Continuity shows real per-device lag.
//
// Triggers (MOBILE_DESKTOP_CONTINUITY): interval + `online` event + visibility
// change. The drain itself respects the SyncPolicy and per-entity ordering.
import { apiUrl, deviceKey, jsonFetch, syncUrl } from './api'
import {
  DEFAULT_SYNC_POLICY,
  policyAllowsSync,
  shouldRunBackgroundSync,
  type PolicyContext,
  type SyncPolicy,
} from './background-sync'
import { detectPlatform } from './platform'
import { drainQueue, loadQueue, pendingCount, type QueueRecord, type SendFn } from './sync-queue'

let timer: ReturnType<typeof setInterval> | undefined
let lastSyncAt = 0
let policy: SyncPolicy = DEFAULT_SYNC_POLICY

export function setSyncPolicy(p: Partial<SyncPolicy>): void {
  policy = { ...policy, ...p }
}

function networkHint(): PolicyContext['network'] {
  if (typeof navigator !== 'undefined' && !navigator.onLine) return 'offline'
  const conn = (navigator as unknown as { connection?: { type?: string; effectiveType?: string } }).connection
  if (conn?.type === 'wifi' || conn?.type === 'ethernet') return 'wifi'
  if (conn?.type === 'cellular') return 'cellular'
  return 'unknown'
}

const send: SendFn = async (record: QueueRecord) => {
  try {
    await jsonFetch(record.url, { method: record.method, body: record.body ? JSON.stringify(record.body) : undefined }, false)
    return { ok: true, status: 200 }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    const match = /^(\d{3})\b/.exec(message)
    return { ok: false, status: match ? Number(match[1]) : 0, error: message }
  }
}

export async function heartbeat(foreground: boolean): Promise<void> {
  const queue = await loadQueue()
  try {
    await jsonFetch(`${syncUrl}/api/sync/heartbeat`, {
      method: 'POST',
      body: JSON.stringify({
        device_key: deviceKey(),
        platform: detectPlatform(),
        pending_mutations: pendingCount(queue),
        foreground,
        network_hint: networkHint(),
      }),
    }, false)
  } catch {
    // heartbeat is best-effort; a missed beat just means stale lag on the server
  }
}

export async function runSyncPass(foreground = true): Promise<void> {
  const queue = await loadQueue()
  const verdict = policyAllowsSync(policy, {
    network: networkHint(),
    batteryLevel: undefined,
    charging: undefined,
  })
  if (!verdict.allowed) return
  const decision = shouldRunBackgroundSync({
    online: networkHint() !== 'offline',
    pendingMutations: pendingCount(queue),
    lastSyncAt: lastSyncAt || undefined,
    now: Date.now(),
  })
  if (!decision.shouldSync && pendingCount(queue) === 0) {
    await heartbeat(foreground)
    return
  }
  await drainQueue(send)
  lastSyncAt = Date.now()
  await heartbeat(foreground)
}

export function startSyncWorker(): void {
  if (typeof window === 'undefined') return
  void runSyncPass(true)
  timer = setInterval(() => { void runSyncPass(false) }, 60_000)
  window.addEventListener('online', () => { void runSyncPass(true) })
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') void runSyncPass(true)
  })
  void apiUrl // worker targets the configured gateway origin
}

export function stopSyncWorker(): void {
  if (timer) clearInterval(timer)
}
