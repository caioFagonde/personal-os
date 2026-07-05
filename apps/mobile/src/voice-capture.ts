// Voice capture queue (Phase E2).
//
// Record audio locally and enqueue the blob queue-first. Transcription happens
// server-side only when model-runtime has whisper configured; until then the
// item carries an HONEST `transcription: unavailable (no model)` state — never
// a fabricated transcript.

export type TranscriptionState =
  | 'unavailable (no model)' // model-runtime has no whisper provider configured
  | 'pending'                // queued, model available, not yet processed
  | 'done'
  | 'failed'

export interface VoiceCaptureRecord {
  id: string
  createdAt: number
  durationMs: number
  mimeType: string
  audioRef: string           // IndexedDB blob key or MinIO object key
  transcription: TranscriptionState
  transcript?: string
}

export interface RuntimeCapabilities {
  audioProvider: string // model-runtime AUDIO_PROVIDER; 'heuristic'/'none' ⇒ no real transcription
}

/** Honest initial transcription state given the runtime's declared capability. */
export function initialTranscriptionState(caps: RuntimeCapabilities): TranscriptionState {
  const provider = (caps.audioProvider || '').toLowerCase()
  const real = provider && !['heuristic', 'none', 'disabled', 'off', 'mock', 'fallback', ''].includes(provider)
  return real ? 'pending' : 'unavailable (no model)'
}

export function buildVoiceCapture(
  input: { id: string; createdAt: number; durationMs: number; mimeType: string; audioRef: string },
  caps: RuntimeCapabilities,
): VoiceCaptureRecord {
  return {
    ...input,
    transcription: initialTranscriptionState(caps),
  }
}

/** Whether this item still needs the server to transcribe it once a model exists. */
export function awaitsTranscription(record: VoiceCaptureRecord): boolean {
  return record.transcription === 'pending' || record.transcription === 'unavailable (no model)'
}
