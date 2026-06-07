import { beforeEach, describe, expect, it, vi } from 'vitest'
import { jsonFetch, researchUrl, uploadFile } from './api'

describe('api service helpers', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('exports research proxy url', () => {
    expect(researchUrl).toContain('/api/proxy/research')
  })

  it('returns parsed JSON on success', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'content-type': 'application/json' } })))
    await expect(jsonFetch('http://example.test/ok')).resolves.toEqual({ ok: true })
  })

  it('throws detailed errors on non-401 failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('bad', { status: 500, statusText: 'Server Error' })))
    await expect(jsonFetch('http://example.test/fail')).rejects.toThrow('500 Server Error')
  })

  it('uploads form data without forcing json content type', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ uploaded: true }), { status: 200, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    const form = new FormData()
    form.set('title', 'Paper')
    await expect(uploadFile('http://example.test/upload', form)).resolves.toEqual({ uploaded: true })
    const calls = fetchMock.mock.calls as unknown as Array<[RequestInfo | URL, RequestInit | undefined]>
    const init = calls[0]?.[1]
    expect(init).toBeDefined()
    expect(init?.method).toBe('POST')
    expect(init?.body).toBe(form)
    expect(init?.headers).not.toHaveProperty('content-type')
  })

  it('retries JSON requests after refresh on 401', async () => {
    localStorage.setItem('personal-os-refresh-token', 'refresh')
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response('unauthorized', { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'new', refresh_token: 'new-refresh' }), { status: 200, headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(jsonFetch('http://example.test/protected')).resolves.toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('retries file uploads by registering when refresh is missing', async () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'device-retry' })
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response('unauthorized', { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'a', refresh_token: 'r' }), { status: 200, headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ uploaded: true }), { status: 200, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(uploadFile('http://example.test/upload', new FormData())).resolves.toEqual({ uploaded: true })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })
})
