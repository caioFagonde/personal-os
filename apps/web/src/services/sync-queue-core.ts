// Pure core of the offline queue v2 (Phase E1). No imports → unit-testable
// without IndexedDB, the network, or the Quasar boot layer.

export type QueueStatus = 'pending' | 'syncing' | 'synced' | 'failed' | 'dead'

export interface QueueRecord {
  id: string
  entity_kind: string
  entity_id: string
  device_seq: number
  vector_hint: Record<string, number>
  url: string
  method: string
  body?: unknown
  createdAt: number
  attempts: number
  status: QueueStatus
  nextAttemptAt: number
  lastError?: string
}

export const BACKOFF_BASE_MS = 2_000
export const BACKOFF_CAP_MS = 5 * 60_000 // 5 min cap (spec)

/** Exponential backoff with full jitter, capped at 5 minutes. `jitter` in [0,1). */
export function nextBackoffMs(attempts: number, jitter = Math.random(), base = BACKOFF_BASE_MS, cap = BACKOFF_CAP_MS): number {
  const raw = Math.min(cap, base * 2 ** Math.max(0, attempts))
  return Math.round(raw / 2 + jitter * (raw / 2)) // full-jitter in [raw/2, raw]
}

/** 4xx (except 408 Request Timeout / 429 Too Many Requests) is permanent →
 *  dead-letter. 5xx, network errors (status 0), 408 and 429 are transient. */
export function classifyFailure(status: number): 'retry' | 'dead_letter' {
  if (status === 0 || status >= 500) return 'retry'
  if (status === 408 || status === 429) return 'retry'
  if (status >= 400) return 'dead_letter'
  return 'retry'
}

/** Per-entity FIFO: at most one in-flight record per entity_id (its oldest
 *  eligible one), parallel across distinct entities. `now` gates backoff. */
export function drainableRecords(records: QueueRecord[], now: number): QueueRecord[] {
  const byEntity = new Map<string, QueueRecord>()
  for (const r of [...records].sort((a, b) => a.device_seq - b.device_seq)) {
    if (r.status !== 'pending' && r.status !== 'failed') continue
    if (r.nextAttemptAt > now) continue
    if (!byEntity.has(r.entity_id)) byEntity.set(r.entity_id, r) // oldest wins (sorted)
  }
  return [...byEntity.values()]
}

export function pendingCount(records: QueueRecord[]): number {
  return records.filter((r) => r.status === 'pending' || r.status === 'failed' || r.status === 'syncing').length
}

export function deadLetterCount(records: QueueRecord[]): number {
  return records.filter((r) => r.status === 'dead').length
}

export interface SendResult { ok: boolean; status: number; error?: string }

/** Fold a send result into a record (mutating a copy is the caller's job). */
export function applyResult(record: QueueRecord, result: SendResult, now: number): QueueRecord {
  const next: QueueRecord = { ...record, attempts: record.attempts + 1 }
  if (result.ok) {
    next.status = 'synced'
  } else if (classifyFailure(result.status) === 'dead_letter') {
    next.status = 'dead'
    next.lastError = result.error || `HTTP ${result.status}`
  } else {
    next.status = 'failed'
    next.lastError = result.error || `HTTP ${result.status}`
    next.nextAttemptAt = now + nextBackoffMs(next.attempts)
  }
  return next
}
