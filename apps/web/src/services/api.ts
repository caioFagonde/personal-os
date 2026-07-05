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
