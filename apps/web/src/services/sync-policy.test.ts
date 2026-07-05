import { describe, expect, it } from 'vitest'
import { DEFAULT_SYNC_POLICY, policyAllowsSync, withinPayloadBudget } from './background-sync'

describe('sync policy', () => {
  it('blocks offline regardless of policy', () => {
    expect(policyAllowsSync(DEFAULT_SYNC_POLICY, { network: 'offline' }).allowed).toBe(false)
  })
  it('honors wifi_only on cellular', () => {
    const policy = { ...DEFAULT_SYNC_POLICY, wifi_only: true }
    expect(policyAllowsSync(policy, { network: 'cellular' }).reason).toBe('wifi-only-policy')
    expect(policyAllowsSync(policy, { network: 'wifi' }).allowed).toBe(true)
  })
  it('honors min_battery unless charging', () => {
    const policy = { ...DEFAULT_SYNC_POLICY, min_battery: 0.2 }
    expect(policyAllowsSync(policy, { network: 'wifi', batteryLevel: 0.1, charging: false }).reason).toBe('below-min-battery')
    expect(policyAllowsSync(policy, { network: 'wifi', batteryLevel: 0.1, charging: true }).allowed).toBe(true)
  })
})

describe('payload budget', () => {
  it('packs records under the per-pass budget but always sends at least one', () => {
    const policy = { ...DEFAULT_SYNC_POLICY, max_payload_mb: 0.000001 } // ~1 byte budget
    const records = [{ body: { a: 1 } }, { body: { b: 2 } }]
    expect(withinPayloadBudget(records, policy)).toHaveLength(1) // never starves the queue
  })
  it('includes everything when the budget is generous', () => {
    const records = [{ body: { a: 1 } }, { body: { b: 2 } }, { body: { c: 3 } }]
    expect(withinPayloadBudget(records, DEFAULT_SYNC_POLICY)).toHaveLength(3)
  })
})
