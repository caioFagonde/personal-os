// Offline queue v2 (Phase E1, closes R-08) — durable storage layer.
//
// IndexedDB-backed (localforage) mutation queue built on the pure core in
// sync-queue-core.ts. Per-entity FIFO ordering, exponential backoff + jitter,
// dead-letter on client errors, optional at-rest encryption. The legacy
// localStorage `offline-queue.ts` stays as the synchronous badge mirror; this
// module is the source of truth the drain worker operates on.
import { localforage } from '../boot/localdb'
import {
  applyResult,
  deadLetterCount,
  drainableRecords,
  pendingCount,
  type QueueRecord,
  type QueueStatus,
  type SendResult,
} from './sync-queue-core'

export type { QueueRecord, QueueStatus, SendResult }
export { nextBackoffMs, classifyFailure, drainableRecords, pendingCount, deadLetterCount, applyResult } from './sync-queue-core'

const STORE_KEY = 'sync-queue-v2'
const SEQ_KEY = 'sync-queue-device-seq'

// --- optional at-rest encryption ----------------------------------------------
// Best-effort: real protection on platforms with a secure key store (Capacitor
// SecureStorage / Tauri stronghold); on plain web the key lives in memory only.
export interface BodyCipher {
  encrypt(plain: string): Promise<string>
  decrypt(cipher: string): Promise<string>
}

export function createWebCryptoCipher(key: CryptoKey): BodyCipher {
  const enc = new TextEncoder()
  const dec = new TextDecoder()
  return {
    async encrypt(plain: string): Promise<string> {
      const iv = crypto.getRandomValues(new Uint8Array(12))
      const ct = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode(plain)))
      const packed = new Uint8Array(iv.length + ct.length)
      packed.set(iv)
      packed.set(ct, iv.length)
      return btoa(String.fromCharCode(...packed))
    },
    async decrypt(cipher: string): Promise<string> {
      const packed = Uint8Array.from(atob(cipher), (c) => c.charCodeAt(0))
      const iv = packed.slice(0, 12)
      const ct = packed.slice(12)
      const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct)
      return dec.decode(pt)
    },
  }
}

let cipher: BodyCipher | null = null
export function setQueueCipher(c: BodyCipher | null): void { cipher = c }

async function readAll(): Promise<QueueRecord[]> {
  const raw = (await localforage.getItem<QueueRecord[]>(STORE_KEY)) ?? []
  if (!cipher) return raw
  return Promise.all(raw.map(async (r) => {
    if (typeof r.body === 'string' && r.body.startsWith('enc:')) {
      try { return { ...r, body: JSON.parse(await cipher!.decrypt(r.body.slice(4))) } } catch { return r }
    }
    return r
  }))
}

async function writeAll(records: QueueRecord[]): Promise<void> {
  const toStore = cipher
    ? await Promise.all(records.map(async (r) => (r.body === undefined ? r : { ...r, body: `enc:${await cipher!.encrypt(JSON.stringify(r.body))}` })))
    : records
  await localforage.setItem(STORE_KEY, toStore)
}

export async function loadQueue(): Promise<QueueRecord[]> {
  return readAll()
}

async function nextDeviceSeq(): Promise<number> {
  const current = (await localforage.getItem<number>(SEQ_KEY)) ?? 0
  const next = current + 1
  await localforage.setItem(SEQ_KEY, next)
  return next
}

function deviceKeyShort(): string {
  try { return (localStorage.getItem('personal-os-device-key') || 'web').slice(0, 24) } catch { return 'web' }
}

export interface EnqueueInput {
  entity_kind: string
  entity_id: string
  url: string
  method: string
  body?: unknown
}

export async function enqueue(input: EnqueueInput): Promise<QueueRecord> {
  const seq = await nextDeviceSeq()
  const record: QueueRecord = {
    id: crypto.randomUUID(),
    entity_kind: input.entity_kind,
    entity_id: input.entity_id,
    device_seq: seq,
    vector_hint: { [deviceKeyShort()]: seq },
    url: input.url,
    method: input.method,
    body: input.body,
    createdAt: Date.now(),
    attempts: 0,
    status: 'pending',
    nextAttemptAt: 0,
  }
  const all = await readAll()
  all.push(record)
  await writeAll(all)
  return record
}

export type SendFn = (record: QueueRecord) => Promise<SendResult>

/** Drain the queue once, respecting per-entity ordering and backoff. A failed
 *  head blocks only its own entity, never the others. */
export async function drainQueue(send: SendFn, now = Date.now()): Promise<{ sent: number; retried: number; dead: number; remaining: number }> {
  const all = await readAll()
  const heads = drainableRecords(all, now)
  let sent = 0
  let retried = 0
  let dead = 0
  for (const head of heads) {
    const idx = all.findIndex((r) => r.id === head.id)
    if (idx < 0) continue
    all[idx] = { ...all[idx], status: 'syncing' }
    let result: SendResult
    try {
      result = await send(head)
    } catch (err) {
      result = { ok: false, status: 0, error: err instanceof Error ? err.message : String(err) }
    }
    all[idx] = applyResult({ ...all[idx], attempts: head.attempts }, result, now)
    if (all[idx].status === 'synced') sent += 1
    else if (all[idx].status === 'dead') dead += 1
    else retried += 1
  }
  await writeAll(all)
  return { sent, retried, dead, remaining: pendingCount(all) }
}

export async function clearSynced(): Promise<void> {
  const all = await readAll()
  await writeAll(all.filter((r) => r.status !== 'synced'))
}

export async function retryDeadLetter(id: string): Promise<void> {
  const all = await readAll()
  const rec = all.find((r) => r.id === id)
  if (rec && rec.status === 'dead') {
    rec.status = 'pending'
    rec.attempts = 0
    rec.nextAttemptAt = 0
    rec.lastError = undefined
    await writeAll(all)
  }
}

export async function removeRecord(id: string): Promise<void> {
  const all = await readAll()
  await writeAll(all.filter((r) => r.id !== id))
}
