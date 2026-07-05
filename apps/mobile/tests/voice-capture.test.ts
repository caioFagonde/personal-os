import { describe, expect, it } from 'vitest'
import { awaitsTranscription, buildVoiceCapture, initialTranscriptionState } from '../src/voice-capture'

const base = { id: 'v1', createdAt: 1, durationMs: 3000, mimeType: 'audio/webm', audioRef: 'blob:1' }

describe('voice capture honesty', () => {
  it('reports unavailable when no real audio model is configured', () => {
    expect(initialTranscriptionState({ audioProvider: 'heuristic' })).toBe('unavailable (no model)')
    expect(initialTranscriptionState({ audioProvider: 'none' })).toBe('unavailable (no model)')
    expect(initialTranscriptionState({ audioProvider: '' })).toBe('unavailable (no model)')
  })
  it('marks pending when a real provider (whisper) is configured', () => {
    expect(initialTranscriptionState({ audioProvider: 'whisper' })).toBe('pending')
    expect(initialTranscriptionState({ audioProvider: 'faster-whisper' })).toBe('pending')
  })
  it('never fabricates a transcript on build', () => {
    const rec = buildVoiceCapture(base, { audioProvider: 'heuristic' })
    expect(rec.transcript).toBeUndefined()
    expect(rec.transcription).toBe('unavailable (no model)')
    expect(awaitsTranscription(rec)).toBe(true)
  })
  it('a done record no longer awaits transcription', () => {
    const rec = buildVoiceCapture(base, { audioProvider: 'whisper' })
    expect(awaitsTranscription({ ...rec, transcription: 'done', transcript: 'hello' })).toBe(false)
  })
})
