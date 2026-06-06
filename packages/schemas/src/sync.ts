export type MergeStrategy = 'lww' | 'field_merge' | 'crdt_text' | 'set_union' | 'counter' | 'manual'

export interface SyncChange {
  event_id: string
  module_id: string
  entity_type: string
  entity_id?: string
  external_id?: string
  action: 'create' | 'update' | 'delete' | 'merge'
  merge_strategy: MergeStrategy
  payload: Record<string, unknown>
  vector_clock: Record<string, number>
  occurred_at: string
}

export interface SyncPullResponse {
  changes: SyncChange[]
  cursor: string
}
