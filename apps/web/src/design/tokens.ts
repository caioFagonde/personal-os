export const navigationModules = [
  { id: 'home', label: 'Command', path: '/', icon: 'mdi-view-dashboard-outline', group: 'Core' },
  { id: 'capture', label: 'Capture', path: '/capture', icon: 'mdi-lightning-bolt-outline', group: 'Core' },
  { id: 'tasks', label: 'Tasks', path: '/tasks', icon: 'mdi-checkbox-marked-circle-auto-outline', group: 'Core' },
  { id: 'study', label: 'Study', path: '/study', icon: 'mdi-school-outline', group: 'Growth' },
  { id: 'study-companion', label: 'Companion', path: '/study-companion', icon: 'mdi-camera-iris', group: 'Growth' },
  { id: 'zettelkasten', label: 'Zettel', path: '/zettelkasten', icon: 'mdi-graph-outline', group: 'Knowledge' },
  { id: 'research', label: 'Research', path: '/research', icon: 'mdi-file-search-outline', group: 'Knowledge' },
  { id: 'geospatial', label: 'Maps', path: '/geospatial', icon: 'mdi-map-search-outline', group: 'Field' },
  { id: 'ar-memory', label: 'AR Memory', path: '/ar-memory', icon: 'mdi-cube-scan', group: 'Field' },
  { id: 'automation', label: 'Automation', path: '/automation', icon: 'mdi-transit-connection-variant', group: 'Ops' },
  { id: 'digital-twin', label: 'Twin', path: '/digital-twin', icon: 'mdi-brain', group: 'Core' },
  { id: 'sync', label: 'Sync', path: '/sync', icon: 'mdi-sync-circle', group: 'Ops' },
  { id: 'offline-queue', label: 'Offline Queue', path: '/offline-queue', icon: 'mdi-cloud-sync-outline', group: 'Ops' },
  { id: 'conflicts', label: 'Conflicts', path: '/conflicts', icon: 'mdi-source-branch-sync', group: 'Ops' },
  { id: 'connectors', label: 'Connectors', path: '/connectors', icon: 'mdi-connection', group: 'Ops' },
  { id: 'connector-worker', label: 'Worker', path: '/connector-worker', icon: 'mdi-truck-fast-outline', group: 'Ops' },
  { id: 'onboarding', label: 'Onboarding', path: '/onboarding', icon: 'mdi-rocket-launch-outline', group: 'Ops' },
  { id: 'backup-restore', label: 'Backup', path: '/backup-restore', icon: 'mdi-cloud-upload-outline', group: 'Ops' },
  { id: 'device-pairing', label: 'Pair Device', path: '/device-pairing', icon: 'mdi-qrcode-scan', group: 'Ops' },
  { id: 'certification', label: 'Certification', path: '/certification', icon: 'mdi-shield-check-outline', group: 'Ops' },
  { id: 'release-center', label: 'Release', path: '/release-center', icon: 'mdi-package-variant-closed-check', group: 'Ops' }
] as const

export const statusTone = {
  ok: { icon: 'mdi-check-circle-outline', label: 'Operational', color: 'positive' },
  degraded: { icon: 'mdi-alert-circle-outline', label: 'Degraded', color: 'warning' },
  offline: { icon: 'mdi-cloud-off-outline', label: 'Offline', color: 'negative' },
  unknown: { icon: 'mdi-help-circle-outline', label: 'Unknown', color: 'grey' }
} as const

export type StatusKey = keyof typeof statusTone

export function normalizeStatus(value: string | undefined | null): StatusKey {
  const text = String(value || '').toLowerCase()
  if (text === 'ok' || text === 'operational' || text === 'healthy') return 'ok'
  if (text === 'degraded' || text === 'warning') return 'degraded'
  if (text === 'offline' || text === 'down' || text === 'error') return 'offline'
  return 'unknown'
}

export function groupNavigation(items = navigationModules) {
  return items.reduce<Record<string, typeof navigationModules[number][]>>((acc, item) => {
    acc[item.group] ||= []
    acc[item.group].push(item)
    return acc
  }, {})
}
