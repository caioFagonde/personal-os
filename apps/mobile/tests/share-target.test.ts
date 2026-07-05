import { describe, expect, it } from 'vitest'
import { captureDeepLink, draftFromQuery, draftFromShare, QUICK_CAPTURE_SHORTCUTS } from '../src/share-target'

describe('share target → capture draft', () => {
  it('maps a shared URL with title', () => {
    const draft = draftFromShare({ type: 'url', url: 'https://x.dev/post', title: 'A Post' })
    expect(draft.source_kind).toBe('share_url')
    expect(draft.text).toBe('A Post\nhttps://x.dev/post')
  })
  it('maps shared plain text', () => {
    expect(draftFromShare({ type: 'text', text: '  buy milk  ' })).toEqual({ text: 'buy milk', source_kind: 'share_text' })
  })
  it('maps a shared image with its attachment uri', () => {
    const draft = draftFromShare({ type: 'image', imageUri: 'content://media/1', text: 'whiteboard' })
    expect(draft.source_kind).toBe('share_image')
    expect(draft.attachmentUri).toBe('content://media/1')
  })
})

describe('capture deep link round trip', () => {
  it('round-trips a draft through the query string', () => {
    const draft = draftFromShare({ type: 'url', url: 'https://x.dev', title: 'T' })
    const link = captureDeepLink(draft)
    expect(link.startsWith('/capture?')).toBe(true)
    const query = Object.fromEntries(new URLSearchParams(link.split('?')[1]))
    const parsed = draftFromQuery(query)
    expect(parsed?.text).toBe(draft.text)
    expect(parsed?.source_kind).toBe('share_url')
  })
  it('returns null for an empty query', () => {
    expect(draftFromQuery({})).toBeNull()
  })
  it('defaults an unknown source_kind to share_text', () => {
    expect(draftFromQuery({ text: 'x', source_kind: 'evil' })?.source_kind).toBe('share_text')
  })
})

describe('quick-capture shortcuts', () => {
  it('offers capture, new task, and today', () => {
    expect(QUICK_CAPTURE_SHORTCUTS.map((s) => s.id)).toEqual(['capture', 'new-task', 'today'])
  })
})
