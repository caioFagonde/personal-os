import { describe, expect, it } from 'vitest'
import { colors, contrastMode, fluidType } from './index'

describe('design system', () => {
  it('exposes stable dark-premium tokens', () => {
    expect(colors.background).toBe('#070a12')
    expect(colors.cyan).toMatch(/^#/)
  })
  it('creates bounded fluid type rules', () => {
    expect(fluidType(16, 32)).toContain('clamp(16px')
    expect(() => fluidType(0, 32)).toThrow()
  })
  it('supports accessibility contrast modes', () => {
    expect(contrastMode(true).text).toBe('#ffffff')
    expect(contrastMode(false).panelOpacity).toBeLessThan(1)
  })
})
