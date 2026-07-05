// Nexus graph registry types + client (Phase B).
// Server-side writes go through packages/graph/py/nexus_graph.py (copied into
// each service); this TS package gives the web/desktop shells typed access to
// the gateway graph read API (/api/graph/*).

export type ObjectKind =
  | 'capture_item' | 'task' | 'project' | 'note' | 'source' | 'decision'
  | 'event' | 'artifact' | 'agent_run' | 'automation' | 'connector_account'
  | 'backup_snapshot' | 'sync_conflict' | 'daily_state' | 'goal' | 'person'
  | 'repository' | 'portfolio_case' | 'habit' | 'reminder'

export type EdgeRel =
  | 'belongs_to_project' | 'derived_from' | 'references' | 'blocks' | 'decided_by'
  | 'about_person' | 'logged_on' | 'produced_by' | 'backs_up' | 'synced_with'
  | 'supports_goal' | 'evidence_for' | 'case_of' | 'mentions' | 'duplicate_of'
  | 'follows'

export interface GraphObject {
  id: string
  kind: ObjectKind | string
  domain_table: string
  domain_id: string
  title: string
  slug: string | null
  status: string | null
  project_id: string | null
  tags: string[]
  meta: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface GraphNeighbor {
  object: GraphObject
  rel: EdgeRel | string
  direction: 'out' | 'in'
  weight: number
}

// 'hybrid' means vector + trigram; 'lexical' is the honest degraded mode when
// no embedding model is available ("lexical search (no embedding model)").
export type SearchMode = 'hybrid' | 'lexical'

export interface GraphSearchHit {
  object: GraphObject
  score: number
  snippet: string | null
}

export interface GraphSearchResponse {
  mode: SearchMode
  label: string
  hits: GraphSearchHit[]
}

export interface GraphSearchRequest {
  text: string
  kinds?: string[]
  k?: number
}

async function asJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`graph request failed: ${response.status}`)
  return response.json() as Promise<T>
}

export async function listObjects(
  apiUrl: string,
  params: { kind?: string; q?: string; limit?: number } = {},
  init: RequestInit = {},
): Promise<GraphObject[]> {
  const query = new URLSearchParams()
  if (params.kind) query.set('kind', params.kind)
  if (params.q) query.set('q', params.q)
  if (params.limit) query.set('limit', String(params.limit))
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return asJson(await fetch(`${apiUrl}/api/graph/objects${suffix}`, init))
}

export async function neighbors(
  apiUrl: string,
  objectId: string,
  rel?: string,
  init: RequestInit = {},
): Promise<GraphNeighbor[]> {
  const suffix = rel ? `?rel=${encodeURIComponent(rel)}` : ''
  return asJson(await fetch(`${apiUrl}/api/graph/objects/${objectId}/neighbors${suffix}`, init))
}

export async function search(
  apiUrl: string,
  request: GraphSearchRequest,
  init: RequestInit = {},
): Promise<GraphSearchResponse> {
  return asJson(await fetch(`${apiUrl}/api/graph/search`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...(init.headers ?? {}) },
    body: JSON.stringify(request),
    ...init,
  }))
}
