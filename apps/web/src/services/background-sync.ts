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

// --- Background sync policy (Phase E1) ----------------------------------------
// Stored in settings and honored by the drain worker. `wifi_only` blocks
// draining on metered connections; `min_battery` blocks below a floor unless
// charging; `max_payload_mb` caps a single drain pass.
export interface SyncPolicy {
  wifi_only: boolean
  min_battery: number // 0..1
  max_payload_mb: number
}

export const DEFAULT_SYNC_POLICY: SyncPolicy = { wifi_only: false, min_battery: 0.15, max_payload_mb: 25 }

export interface PolicyContext {
  network: 'wifi' | 'cellular' | 'offline' | 'unknown'
  batteryLevel?: number
  charging?: boolean
}

export interface PolicyVerdict {
  allowed: boolean
  reason: string
}

export function policyAllowsSync(policy: SyncPolicy, ctx: PolicyContext): PolicyVerdict {
  if (ctx.network === 'offline') return { allowed: false, reason: 'offline' }
  if (policy.wifi_only && ctx.network === 'cellular') return { allowed: false, reason: 'wifi-only-policy' }
  if (!ctx.charging && (ctx.batteryLevel ?? 1) < policy.min_battery) return { allowed: false, reason: 'below-min-battery' }
  return { allowed: true, reason: 'ok' }
}

/** Greedily pack drain candidates under the policy's per-pass payload budget. */
export function withinPayloadBudget<T extends { body?: unknown }>(records: T[], policy: SyncPolicy): T[] {
  const budget = policy.max_payload_mb * 1_048_576
  const out: T[] = []
  let used = 0
  for (const r of records) {
    const size = r.body === undefined ? 256 : new Blob([JSON.stringify(r.body)]).size
    if (used + size > budget && out.length) break
    out.push(r)
    used += size
  }
  return out
}
