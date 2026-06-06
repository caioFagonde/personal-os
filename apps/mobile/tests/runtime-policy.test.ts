import { describe, expect, it } from 'vitest'
import { mobileRuntimePolicy } from '../src/runtime-policy'

describe('mobile runtime policy', () => {
  it('blocks background sync offline', () => {
    expect(mobileRuntimePolicy({ platform: 'android', network: 'offline', batteryLevel: 1, charging: true, pendingMutations: 3 }).canBackgroundSync).toBe(false)
  })
  it('allows urgent queue sync even on low battery', () => {
    const policy = mobileRuntimePolicy({ platform: 'android', network: 'cellular', batteryLevel: 0.1, charging: false, pendingMutations: 12 })
    expect(policy.canBackgroundSync).toBe(true)
    expect(policy.preferWifi).toBe(true)
  })
  it('raises notification priority for large queues', () => {
    expect(mobileRuntimePolicy({ platform: 'ios', network: 'wifi', batteryLevel: 0.5, charging: false, pendingMutations: 30 }).notificationPriority).toBe('high')
  })
})
