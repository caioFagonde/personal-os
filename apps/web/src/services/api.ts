export const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080'
export const syncUrl = import.meta.env.VITE_SYNC_URL || 'http://localhost:8081'
export const commandUrl = import.meta.env.VITE_COMMAND_BUS_URL || 'http://localhost:8082'
export const moduleUrl = import.meta.env.VITE_MODULE_API_URL || 'http://localhost:8083'

export async function jsonFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: { 'content-type': 'application/json', ...(options.headers || {}) }
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json()
}

export function deviceKey(): string {
  const key = 'personal-os-device-key'
  let value = localStorage.getItem(key)
  if (!value) {
    value = `web-${crypto.randomUUID()}`
    localStorage.setItem(key, value)
  }
  return value
}
