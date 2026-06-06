import { describe, expect, it } from 'vitest'
import { detectPlatform, preferredLayout, safeAreaStyle } from './platform'

describe('platform helpers', () => {
  it('detects mobile from UA or small viewport', () => {
    expect(detectPlatform('Mozilla Android', 1200)).toBe('mobile')
    expect(detectPlatform('Desktop Chrome', 390)).toBe('mobile')
  })
  it('detects desktop and applies drawer layout', () => {
    expect(detectPlatform('Macintosh', 1440)).toBe('desktop')
    expect(preferredLayout('desktop').drawer).toBe(true)
    expect(preferredLayout('mobile').bottomNav).toBe(true)
  })
  it('uses safe-area padding on mobile', () => {
    expect(safeAreaStyle('mobile').paddingBottom).toContain('safe-area')
  })
})
