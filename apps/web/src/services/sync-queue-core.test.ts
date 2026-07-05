import { describe, expect, it } from 'vitest'
import {
  applyResult,
  BACKOFF_CAP_MS,
  classifyFailure,
  deadLetterCount,
  drainableRecords,
  nextBackoffMs,
  pendingCount,
  type QueueRecord,
} from './sync-queue-core'

function rec(over: Partial<QueueRecord>): QueueRecord {
  return {
    id: over.id ?? 'r', entity_kind: 'task', entity_id: over.entity_id ?? 'e1',
    device_seq: over.device_seq ?? 1, vector_hint: {}, url: '/x', method: 'POST',
    createdAt: 0, attempts: over.attempts ?? 0, status: over.status ?? 'pending',
    nextAttemptAt: over.nextAttemptAt ?? 0, ...over,
  }
}

describe('backoff', () => {
  it('is monotonic and capped at 5 minutes', () => {
    expect(nextBackoffMs(0, 0)).toBe(1_000) // base/2 with zero jitter
    expect(nextBackoffMs(1, 0)).toBe(2_000)
    expect(nextBackoffMs(20, 1)).toBe(BACKOFF_CAP_MS)
    expect(nextBackoffMs(20, 0)).toBe(BACKOFF_CAP_MS / 2)
  })
  it('adds jitter within [raw/2, raw]', () => {
    const low = nextBackoffMs(3, 0)
    const high = nextBackoffMs(3, 0.999)
    expect(high).toBeGreaterThan(low)
  })
})

describe('failure classification', () => {
  it('dead-letters permanent client errors', () => {
    expect(classifyFailure(400)).toBe('dead_letter')
    expect(classifyFailure(403)).toBe('dead_letter')
    expect(classifyFailure(404)).toBe('dead_letter')
  })
  it('retries transient failures', () => {
    expect(classifyFailure(0)).toBe('retry')   // network
    expect(classifyFailure(500)).toBe('retry')
    expect(classifyFailure(503)).toBe('retry')
    expect(classifyFailure(408)).toBe('retry')  // request timeout
    expect(classifyFailure(429)).toBe('retry')  // rate limited
  })
})

describe('per-entity FIFO ordering', () => {
  it('emits at most one head per entity, oldest first, parallel across entities', () => {
    const records = [
      rec({ id: 'a2', entity_id: 'A', device_seq: 2 }),
      rec({ id: 'a1', entity_id: 'A', device_seq: 1 }),
      rec({ id: 'b1', entity_id: 'B', device_seq: 3 }),
    ]
    const heads = drainableRecords(records, 1000)
    expect(heads.map((r) => r.id).sort()).toEqual(['a1', 'b1']) // a1 (oldest of A) + B's head
  })
  it('skips records still in backoff', () => {
    const records = [rec({ id: 'a1', entity_id: 'A', status: 'failed', nextAttemptAt: 5000 })]
    expect(drainableRecords(records, 1000)).toHaveLength(0)
    expect(drainableRecords(records, 6000)).toHaveLength(1)
  })
  it('ignores synced and dead records', () => {
    const records = [rec({ id: 's', status: 'synced' }), rec({ id: 'd', entity_id: 'D', status: 'dead' })]
    expect(drainableRecords(records, 1000)).toHaveLength(0)
  })
})

describe('applyResult', () => {
  it('marks synced on ok', () => {
    expect(applyResult(rec({}), { ok: true, status: 200 }, 0).status).toBe('synced')
  })
  it('dead-letters a 4xx and schedules a retry for a 5xx', () => {
    expect(applyResult(rec({}), { ok: false, status: 422 }, 0).status).toBe('dead')
    const retried = applyResult(rec({ attempts: 0 }), { ok: false, status: 503 }, 1000)
    expect(retried.status).toBe('failed')
    expect(retried.nextAttemptAt).toBeGreaterThan(1000)
  })
})

describe('counts', () => {
  it('counts pending (incl. failed/syncing) and dead separately', () => {
    const records = [rec({ status: 'pending' }), rec({ id: 'f', status: 'failed' }), rec({ id: 'd', status: 'dead' }), rec({ id: 's', status: 'synced' })]
    expect(pendingCount(records)).toBe(2)
    expect(deadLetterCount(records)).toBe(1)
  })
})
