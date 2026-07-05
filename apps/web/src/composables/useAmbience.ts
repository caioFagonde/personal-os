/**
 * Shared ambience state for the Big Picture shell.
 *
 * The focused tile sets the accent; the WebGL aurora tweens toward it.
 * Parallax is a normalized pointer/stick offset the background drifts with.
 */
import { reactive, readonly } from 'vue'

interface AmbienceState {
  accent: string
  accent2: string
  /** -1..1 normalized parallax offsets */
  parallaxX: number
  parallaxY: number
  /** 0..1 — how dimmed the aurora is (detail pages dim it so content reads) */
  dim: number
}

const state = reactive<AmbienceState>({
  accent: '#7DD3FC',
  accent2: '#A78BFA',
  parallaxX: 0,
  parallaxY: 0,
  dim: 0,
})

export function setAmbience(accent: string, accent2: string) {
  state.accent = accent
  state.accent2 = accent2
}

export function setParallax(x: number, y: number) {
  state.parallaxX = Math.max(-1, Math.min(1, x))
  state.parallaxY = Math.max(-1, Math.min(1, y))
}

export function setDim(dim: number) {
  state.dim = Math.max(0, Math.min(1, dim))
}

export function useAmbience() {
  return readonly(state)
}

export function hexToRgb01(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  const v = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const n = parseInt(v, 16)
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]
}
