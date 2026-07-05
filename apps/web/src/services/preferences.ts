// UX preferences (Phase C5). Density is a client preference applied as a body
// class so the theme layer can tighten spacing; persisted in localStorage.
export type Density = 'comfortable' | 'compact'

const DENSITY_KEY = 'nexus-density'

export function loadDensity(): Density {
  return localStorage.getItem(DENSITY_KEY) === 'compact' ? 'compact' : 'comfortable'
}

export function applyDensity(density: Density) {
  localStorage.setItem(DENSITY_KEY, density)
  document.body.classList.toggle('density-compact', density === 'compact')
}

export function initDensity() {
  applyDensity(loadDensity())
}
