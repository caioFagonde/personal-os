export const colors = {
  background: '#070a12',
  panel: 'rgba(18, 27, 46, 0.72)',
  text: '#eff6ff',
  muted: '#9fb0cf',
  cyan: '#7dd3fc',
  violet: '#a78bfa',
  green: '#34d399',
  amber: '#fbbf24',
  red: '#fb7185'
} as const

export const radii = { sm: 12, md: 18, lg: 24, xl: 32 } as const
export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48 } as const

export function fluidType(minPx: number, maxPx: number, minViewport = 360, maxViewport = 1440) {
  if (minPx <= 0 || maxPx < minPx) throw new Error('invalid fluid type bounds')
  const slope = (maxPx - minPx) / (maxViewport - minViewport)
  const intercept = minPx - slope * minViewport
  return `clamp(${minPx}px, ${intercept.toFixed(4)}px + ${(slope * 100).toFixed(4)}vw, ${maxPx}px)`
}

export function contrastMode(highContrast: boolean) {
  return highContrast
    ? { border: 'rgba(255,255,255,0.42)', panelOpacity: 0.96, text: '#ffffff' }
    : { border: 'rgba(152,184,255,0.18)', panelOpacity: 0.72, text: colors.text }
}
