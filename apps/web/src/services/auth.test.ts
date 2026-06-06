import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authHeaders, buildRegistrationPayload, clearTokens, deviceKey, platformKind, setTokens } from './auth'

describe('auth service', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('classifies mobile user agents', () => {
    expect(platformKind('Mozilla/5.0 Android')).toBe('mobile')
    expect(platformKind('Mozilla/5.0 Macintosh')).toBe('desktop')
  })

  it('persists a stable device key', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'fixed-id' })
    expect(deviceKey()).toBe('desktop-fixed-id')
    expect(deviceKey()).toBe('desktop-fixed-id')
  })

  it('adds bearer headers only when a token exists', () => {
    expect(authHeaders()).toEqual({})
    setTokens({ access_token: 'abc', refresh_token: 'def' })
    expect(authHeaders()).toEqual({ authorization: 'Bearer abc' })
    clearTokens()
    expect(authHeaders()).toEqual({})
  })

  it('builds registration payload from local device state', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'device-1' })
    const payload = buildRegistrationPayload()
    expect(payload.device_key).toContain('device-1')
    expect(payload.kind).toMatch(/mobile|desktop|web/)
    expect(payload.build_channel).toBeTruthy()
  })
})
