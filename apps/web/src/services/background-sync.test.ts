import { describe, expect, it } from 'vitest'
import { nextSyncDelayMs, shouldRunBackgroundSync } from './background-sync'

describe('background sync decisioning', () => {
  it('blocks offline and low battery sync', () => {
    expect(shouldRunBackgroundSync({ online: false, pendingMutations: 2, now: 10 }).reason).toBe('offline')
    expect(shouldRunBackgroundSync({ online: true, pendingMutations: 2, batteryLevel: 0.1, charging: false, now: 10 }).reason).toBe('low-battery')
  })
  it('prioritizes mutation queues', () => {
    expect(shouldRunBackgroundSync({ online: true, pendingMutations: 30, now: 10 }).priority).toBe('urgent')
    expect(shouldRunBackgroundSync({ online: true, pendingMutations: 1, now: 10 }).reason).toBe('pending-mutations')
  })
  it('syncs stale clients and schedules delays', () => {
    const decision = shouldRunBackgroundSync({ online: true, pendingMutations: 0, lastSyncAt: 0, now: 20 * 60 * 1000 })
    expect(decision.shouldSync).toBe(true)
    expect(nextSyncDelayMs(decision)).toBe(60_000)
    expect(nextSyncDelayMs({ shouldSync: false, reason: 'fresh', priority: 'idle' })).toBe(300_000)
  })
})
