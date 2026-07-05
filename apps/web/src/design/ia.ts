// Phase C information architecture (UX_PRODUCT_SPEC: 13 primary surfaces).
// Extends the module registry WITHOUT touching tokens.ts: new surfaces are
// declared here and concatenated for palette/nav consumers.
import { allModules } from './tokens'

export interface SurfaceModule {
  id: string
  label: string
  path: string
  icon: string
  group: string
}

// New Phase C surfaces (routes exist in router/routes.ts).
export const phaseCSurfaces: SurfaceModule[] = [
  { id: 'today', label: 'Today / Focus', path: '/today', icon: 'mdi-calendar-today', group: 'Core' },
  { id: 'projects', label: 'Projects', path: '/projects', icon: 'mdi-folder-star-outline', group: 'Core' },
  { id: 'continuity', label: 'Continuity', path: '/continuity', icon: 'mdi-shield-sync-outline', group: 'Ops' },
  { id: 'ops', label: 'Ops', path: '/ops', icon: 'mdi-wrench-outline', group: 'Ops' },
]

// Old path → canonical Phase C path. Router adds redirects for entries here
// whose old page has been superseded; paths whose pages remain first-class
// are aliases only (both routes render).
export const routeAliases: Record<string, string> = {
  '/daily': '/today',
  '/agents': '/coding-agent',
  '/twin': '/digital-twin',
  '/notes': '/zettelkasten',
}

// allModules is declared `as const`; widen to the plain interface here.
const base: SurfaceModule[] = allModules.map((m) => ({ id: m.id, label: m.label, path: m.path, icon: m.icon, group: m.group }))
const seen = new Set<string>(base.map((m) => m.id))
export const surfaceModules: SurfaceModule[] = [
  ...base,
  ...phaseCSurfaces.filter((m) => !seen.has(m.id)),
]
