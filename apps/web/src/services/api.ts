import { authHeaders, deviceKey, refreshToken, registerDevice } from './auth'

export const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080'
export const syncUrl = import.meta.env.VITE_SYNC_URL || `${apiUrl}/api/proxy/sync`
export const commandUrl = import.meta.env.VITE_COMMAND_BUS_URL || `${apiUrl}/api/proxy/commands`
export const moduleUrl = import.meta.env.VITE_MODULE_API_URL || `${apiUrl}/api/proxy/modules`
export const researchUrl = import.meta.env.VITE_RESEARCH_URL || `${apiUrl}/api/proxy/research`
export const automationUrl = import.meta.env.VITE_AUTOMATION_URL || `${apiUrl}/api/proxy/automation`
export const digitalTwinUrl = import.meta.env.VITE_DIGITAL_TWIN_URL || `${apiUrl}/api/proxy/digital-twin`
export const captureUrl = import.meta.env.VITE_CAPTURE_URL || `${apiUrl}/api/proxy/capture`
export const studyCompanionUrl = import.meta.env.VITE_STUDY_COMPANION_URL || `${apiUrl}/api/proxy/study-companion`
export const connectorsUrl = import.meta.env.VITE_CONNECTORS_URL || `${apiUrl}/api/proxy/connectors`
export const modelRuntimeUrl = import.meta.env.VITE_MODEL_RUNTIME_URL || `${apiUrl}/api/proxy/model-runtime`
export const codingAgentUrl = import.meta.env.VITE_CODING_AGENT_URL || `${apiUrl}/api/proxy/coding-agent`
export const intelligenceUrl = import.meta.env.VITE_INTELLIGENCE_URL || `${apiUrl}/api/proxy/intelligence`

export { deviceKey }

export interface Attachment {
  id: string
  entity_id: string | null
  module_id: string | null
  filename: string
  content_type: string | null
  size_bytes: number
  checksum: string
  sync_state: string
  encrypted: boolean
  created_at: string | null
  download_path: string
}

// Browse artifacts stored on the PC (PDFs and other files). Reachable from any
// paired device over Tailscale via the authenticated gateway sync proxy.
export async function listAttachments(params: { module_id?: string; entity_id?: string; limit?: number } = {}): Promise<Attachment[]> {
  const qs = new URLSearchParams()
  if (params.module_id) qs.set('module_id', params.module_id)
  if (params.entity_id) qs.set('entity_id', params.entity_id)
  if (params.limit) qs.set('limit', String(params.limit))
  const q = qs.toString()
  return jsonFetch<Attachment[]>(`${syncUrl}/api/attachments${q ? `?${q}` : ''}`)
}

// Fetch an artifact's bytes with auth headers (a plain <a> can't carry the
// bearer token) and hand back an object URL suitable for a viewer or download.
export async function fetchAttachmentObjectUrl(id: string): Promise<string> {
  const res = await fetch(`${syncUrl}/api/attachments/${id}/download`, { headers: { ...authHeaders() } })
  if (res.status === 401) {
    try { await refreshToken(apiUrl) } catch { await registerDevice(apiUrl) }
    const retry = await fetch(`${syncUrl}/api/attachments/${id}/download`, { headers: { ...authHeaders() } })
    if (!retry.ok) throw new Error(`${retry.status} ${retry.statusText}`)
    return URL.createObjectURL(await retry.blob())
  }
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return URL.createObjectURL(await res.blob())
}

export async function jsonFetch<T>(url: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = {
    'content-type': 'application/json',
    ...authHeaders(),
    ...(options.headers || {})
  }
  const res = await fetch(url, { ...options, headers })
  if (res.status === 401 && retry && !url.includes('/api/devices/register')) {
    try {
      await refreshToken(apiUrl)
    } catch {
      await registerDevice(apiUrl)
    }
    return jsonFetch<T>(url, options, false)
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json()
}


export async function uploadFile<T>(url: string, form: FormData, retry = true): Promise<T> {
  const headers = {
    ...authHeaders()
  }
  const res = await fetch(url, { method: 'POST', body: form, headers })
  if (res.status === 401 && retry) {
    try {
      await refreshToken(apiUrl)
    } catch {
      await registerDevice(apiUrl)
    }
    return uploadFile<T>(url, form, false)
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json()
}
