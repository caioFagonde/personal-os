import { describe, expect, it } from 'vitest'
import { groupNavigation, navigationModules, normalizeStatus } from './tokens'

describe('design tokens', () => {
  it('normalizes service status consistently', () => {
    expect(normalizeStatus('healthy')).toBe('ok')
    expect(normalizeStatus('down')).toBe('offline')
    expect(normalizeStatus(undefined)).toBe('unknown')
  })
  it('groups navigation without dropping modules', () => {
    const grouped = groupNavigation()
    const count = Object.values(grouped).reduce((sum, group) => sum + group.length, 0)
    expect(count).toBe(navigationModules.length)
    expect(grouped.Knowledge.map((m) => m.id)).toContain('research')
  })
})
