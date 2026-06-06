import { beforeEach, describe, expect, it, vi } from 'vitest'
import { clearSynced, enqueueOfflineMutation, loadOfflineQueue, saveOfflineQueue } from './offline-queue'

describe('offline queue helpers', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('loads an empty queue and recovers from corrupt storage', () => {
    expect(loadOfflineQueue()).toEqual([])
    localStorage.setItem('personal-os-offline-mutations', '{bad json')
    expect(loadOfflineQueue()).toEqual([])
  })

  it('enqueues deterministic pending mutations', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'mutation-1' })
    vi.setSystemTime?.(new Date('2026-01-01T00:00:00Z'))
    const item = enqueueOfflineMutation({ url: '/api/x', method: 'POST', body: { ok: true } })
    expect(item.id).toBe('mutation-1')
    expect(item.status).toBe('pending')
    expect(item.attempts).toBe(0)
    expect(loadOfflineQueue()).toHaveLength(1)
  })

  it('clears only synced mutations', () => {
    saveOfflineQueue([
      { id: 'a', url: '/a', method: 'POST', createdAt: 1, attempts: 0, status: 'synced' },
      { id: 'b', url: '/b', method: 'POST', createdAt: 2, attempts: 1, status: 'failed', error: 'boom' }
    ])
    clearSynced()
    expect(loadOfflineQueue().map((m) => m.id)).toEqual(['b'])
  })
})
