const ACCESS_TOKEN_KEY = 'personal-os-access-token'
const REFRESH_TOKEN_KEY = 'personal-os-refresh-token'
const DEVICE_KEY = 'personal-os-device-key'

export type TokenPair = {
  access_token: string
  refresh_token: string
  token_type?: string
  expires_in?: number
  device_id?: string
}

export function platformKind(userAgent = navigator.userAgent): 'mobile' | 'desktop' | 'web' {
  if (/Android|iPhone|iPad|iPod/i.test(userAgent)) return 'mobile'
  if (/Tauri|Electron|Windows|Macintosh|Linux/i.test(userAgent)) return 'desktop'
  return 'web'
}

export function deviceKey(): string {
  let value = localStorage.getItem(DEVICE_KEY)
  if (!value) {
    const random = typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`
    value = `${platformKind()}-${random}`
    localStorage.setItem(DEVICE_KEY, value)
  }
  return value
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens(pair: TokenPair): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, pair.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, pair.refresh_token)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function authHeaders(): Record<string, string> {
  const token = getAccessToken()
  return token ? { authorization: `Bearer ${token}` } : {}
}

export function buildRegistrationPayload() {
  const kind = platformKind()
  return {
    device_key: deviceKey(),
    name: `${kind} shell`,
    kind,
    platform: navigator.platform || 'unknown',
    app_version: import.meta.env.VITE_APP_VERSION || '0.4.0',
    build_channel: import.meta.env.VITE_BUILD_CHANNEL || 'dev'
  }
}

export async function registerDevice(apiUrl: string): Promise<TokenPair> {
  const response = await fetch(`${apiUrl}/api/devices/register`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(buildRegistrationPayload())
  })
  if (!response.ok) {
    throw new Error(`device registration failed: ${response.status} ${await response.text()}`)
  }
  const pair = await response.json() as TokenPair
  setTokens(pair)
  return pair
}

export async function refreshToken(apiUrl: string): Promise<TokenPair> {
  const refresh_token = getRefreshToken()
  if (!refresh_token) throw new Error('missing refresh token')
  const response = await fetch(`${apiUrl}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ refresh_token })
  })
  if (!response.ok) {
    clearTokens()
    throw new Error(`token refresh failed: ${response.status} ${await response.text()}`)
  }
  const pair = await response.json() as TokenPair
  setTokens(pair)
  return pair
}
