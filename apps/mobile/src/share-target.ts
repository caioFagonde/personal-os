// Android share-target + quick-capture (Phase E2).
//
// The single biggest daily-use unlock: Android's share sheet (text/URL/image)
// routes into the app, which opens Capture pre-filled and saves queue-first.
// The native intent is declared in android-share-target.xml (applied after
// `npx cap add android`); this module holds the pure payload → capture-draft
// mapping, plus the deep-link the web Capture page reads.

export interface SharedPayload {
  type: 'text' | 'url' | 'image'
  text?: string
  url?: string
  imageUri?: string
  title?: string
}

export interface CaptureDraft {
  text: string
  source_kind: 'share_text' | 'share_url' | 'share_image'
  attachmentUri?: string
}

/** Map an incoming Android/iOS share payload to a Capture draft. */
export function draftFromShare(payload: SharedPayload): CaptureDraft {
  if (payload.type === 'url') {
    const title = payload.title ? `${payload.title}\n` : ''
    return { text: `${title}${payload.url ?? ''}`.trim(), source_kind: 'share_url' }
  }
  if (payload.type === 'image') {
    return { text: (payload.text ?? payload.title ?? 'Shared image').trim(), source_kind: 'share_image', attachmentUri: payload.imageUri }
  }
  return { text: (payload.text ?? '').trim(), source_kind: 'share_text' }
}

/** Deep link the Capture page opens with, e.g. /capture?share_text=... */
export function captureDeepLink(draft: CaptureDraft): string {
  const params = new URLSearchParams({ text: draft.text, source_kind: draft.source_kind })
  if (draft.attachmentUri) params.set('attachment', draft.attachmentUri)
  return `/capture?${params.toString()}`
}

/** Parse a Capture deep link back into a draft (used by the web Capture page). */
export function draftFromQuery(query: Record<string, string | undefined>): CaptureDraft | null {
  const text = query.text
  const source = query.source_kind
  if (!text && !query.attachment) return null
  const validSources = ['share_text', 'share_url', 'share_image'] as const
  const source_kind = validSources.includes(source as (typeof validSources)[number])
    ? (source as CaptureDraft['source_kind'])
    : 'share_text'
  return { text: text ?? '', source_kind, attachmentUri: query.attachment }
}

// App-shortcut / quick-capture tile targets (long-press icon).
export const QUICK_CAPTURE_SHORTCUTS = [
  { id: 'capture', label: 'Capture', route: '/capture' },
  { id: 'new-task', label: 'New task', route: '/tasks?new=1' },
  { id: 'today', label: 'Today', route: '/today' },
] as const
