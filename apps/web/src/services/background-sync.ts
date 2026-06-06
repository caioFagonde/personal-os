export interface SyncCandidate {
  pendingMutations: number
  lastSyncAt?: number
  online: boolean
  batteryLevel?: number
  charging?: boolean
  now: number
}

export interface SyncDecision {
  shouldSync: boolean
  reason: string
  priority: 'idle' | 'normal' | 'urgent'
}

export function shouldRunBackgroundSync(input: SyncCandidate): SyncDecision {
  if (!input.online) return { shouldSync: false, reason: 'offline', priority: 'idle' }
  if ((input.batteryLevel ?? 1) < 0.15 && !input.charging) return { shouldSync: false, reason: 'low-battery', priority: 'idle' }
  if (input.pendingMutations > 25) return { shouldSync: true, reason: 'large-queue', priority: 'urgent' }
  if (input.pendingMutations > 0) return { shouldSync: true, reason: 'pending-mutations', priority: 'normal' }
  const ageMs = input.lastSyncAt ? input.now - input.lastSyncAt : Number.POSITIVE_INFINITY
  if (ageMs > 15 * 60 * 1000) return { shouldSync: true, reason: 'stale', priority: 'normal' }
  return { shouldSync: false, reason: 'fresh', priority: 'idle' }
}

export function nextSyncDelayMs(decision: SyncDecision): number {
  if (decision.priority === 'urgent') return 5_000
  if (decision.priority === 'normal') return 60_000
  return 5 * 60_000
}
