export interface OfflineMutation {
  id: string
  url: string
  method: string
  body?: unknown
  createdAt: number
  attempts: number
  status: 'pending' | 'syncing' | 'synced' | 'failed'
  error?: string
}
const KEY = 'personal-os-offline-mutations'
export function loadOfflineQueue(): OfflineMutation[] {
  try { return JSON.parse(localStorage.getItem(KEY) || '[]') } catch { return [] }
}
export function saveOfflineQueue(items: OfflineMutation[]) { localStorage.setItem(KEY, JSON.stringify(items)) }
export function enqueueOfflineMutation(input: Omit<OfflineMutation, 'id' | 'createdAt' | 'attempts' | 'status'>): OfflineMutation {
  const item: OfflineMutation = { ...input, id: crypto.randomUUID(), createdAt: Date.now(), attempts: 0, status: 'pending' }
  saveOfflineQueue([...loadOfflineQueue(), item])
  return item
}
export function clearSynced() { saveOfflineQueue(loadOfflineQueue().filter((m) => m.status !== 'synced')) }
