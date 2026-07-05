// Client for the gateway graph read API (Phase B4).
// Mirrors packages/graph/src/index.ts types, but rides the app's jsonFetch
// (auth headers + token refresh).
import { apiUrl, jsonFetch } from './api'

export interface GraphObject {
  id: string
  kind: string
  domain_table: string
  domain_id: string
  title: string
  slug: string | null
  status: string | null
  project_id: string | null
  tags: string[]
  created_at: string
  updated_at: string
}

export interface GraphNeighbor {
  object: GraphObject
  rel: string
  direction: 'out' | 'in'
  weight: number
}

export interface GraphSearchHit {
  object: GraphObject
  score: number
  snippet: string | null
}

export interface GraphSearchResponse {
  // 'lexical' is the honest degraded mode: "lexical search (no embedding model)".
  mode: 'hybrid' | 'lexical'
  label: string
  hits: GraphSearchHit[]
}

export function listGraphObjects(params: { kind?: string; q?: string; domainId?: string; limit?: number } = {}) {
  const query = new URLSearchParams()
  if (params.kind) query.set('kind', params.kind)
  if (params.q) query.set('q', params.q)
  if (params.domainId) query.set('domain_id', params.domainId)
  if (params.limit) query.set('limit', String(params.limit))
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return jsonFetch<GraphObject[]>(`${apiUrl}/api/graph/objects${suffix}`)
}

// Resolve a domain row (e.g. notes/<id>) to its registry object, or null.
export async function graphObjectFor(kind: string, domainId: string): Promise<GraphObject | null> {
  const rows = await listGraphObjects({ kind, domainId, limit: 1 })
  return rows[0] ?? null
}

export function graphNeighbors(objectId: string, rel?: string) {
  const suffix = rel ? `?rel=${encodeURIComponent(rel)}` : ''
  return jsonFetch<GraphNeighbor[]>(`${apiUrl}/api/graph/objects/${objectId}/neighbors${suffix}`)
}

export function graphSearch(text: string, kinds: string[] = [], k = 12) {
  return jsonFetch<GraphSearchResponse>(`${apiUrl}/api/graph/search`, {
    method: 'POST',
    body: JSON.stringify({ text, kinds, k }),
  })
}

const kindRoutes: Record<string, (o: GraphObject) => string> = {
  task: () => '/tasks',
  capture_item: () => '/capture',
  note: () => '/zettelkasten',
  project: (o) => `/projects?open=${o.domain_id}`,
  daily_state: () => '/daily',
  source: () => '/research',
  goal: () => '/digital-twin',
  event: () => '/digital-twin',
  agent_run: () => '/coding-agent',
}

export function routeForObject(object: GraphObject): string {
  const resolve = kindRoutes[object.kind]
  return resolve ? resolve(object) : '/command-center'
}

export const kindIcons: Record<string, string> = {
  task: 'mdi-checkbox-marked-circle-outline',
  capture_item: 'mdi-tray-arrow-down',
  note: 'mdi-note-text-outline',
  project: 'mdi-folder-star-outline',
  daily_state: 'mdi-calendar-today',
  source: 'mdi-file-document-outline',
  goal: 'mdi-flag-outline',
  event: 'mdi-timeline-clock-outline',
  agent_run: 'mdi-robot-outline',
}
