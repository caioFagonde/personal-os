<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Mobile Continuity" title="Offline Queue" subtitle="Durable, per-entity mutation queue (IndexedDB). Drains with backoff; 4xx dead-letters for review.">
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh" @click="load" />
        <q-btn color="secondary" icon="mdi-plus" label="Create test mutation" @click="createTest" />
        <q-btn outline icon="mdi-sync" label="Drain now" :loading="draining" @click="drainNow" />
        <q-btn outline label="Clear synced" @click="clear" />
      </template>
    </NexusPageHero>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Queue ({{ pending.length }} pending)</div>
      </q-card-section>
      <q-table v-if="pending.length" :rows="pending" :columns="columns" row-key="id" flat class="nexus-table">
        <template #body-cell-body="props">
          <q-td :props="props"><pre class="mini-code">{{ JSON.stringify(props.row.body) }}</pre></q-td>
        </template>
      </q-table>
      <NexusEmptyState v-else icon="mdi-cloud-check-outline" message="Offline queue is empty." hint="All mutations have been synced." />
    </q-card>

    <!-- Dead-letter: 4xx mutations that will not retry until you say so -->
    <q-card class="glass-card" v-if="dead.length" data-testid="dead-letter">
      <q-card-section>
        <div class="row items-center justify-between">
          <div class="text-h6 text-negative">Dead-letter ({{ dead.length }})</div>
          <span class="text-caption" style="color:var(--nexus-muted)">Rejected with a client error — fix and retry, or discard.</span>
        </div>
      </q-card-section>
      <q-list separator>
        <q-item v-for="item in dead" :key="item.id">
          <q-item-section avatar><q-icon name="mdi-alert-octagon-outline" color="negative" /></q-item-section>
          <q-item-section>
            <q-item-label>{{ item.method }} {{ item.url }}</q-item-label>
            <q-item-label caption>{{ item.entity_kind }}/{{ item.entity_id }} · {{ item.lastError }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <div class="row q-gutter-xs">
              <q-btn flat size="sm" color="primary" label="Retry" @click="retry(item.id)" />
              <q-btn flat size="sm" color="grey" label="Discard" @click="discard(item.id)" />
            </div>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { QTableColumn } from 'quasar'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { clearSynced, deadLetterCount, drainQueue, enqueue, loadQueue, removeRecord, retryDeadLetter, type QueueRecord } from '../services/sync-queue'

const all = ref<QueueRecord[]>([])
const pending = ref<QueueRecord[]>([])
const dead = ref<QueueRecord[]>([])
const draining = ref(false)

const columns: QTableColumn[] = [
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'entity', label: 'Entity', field: (r: QueueRecord) => `${r.entity_kind}/${r.entity_id}`, align: 'left' },
  { name: 'method', label: 'Method', field: 'method', align: 'left' },
  { name: 'url', label: 'URL', field: 'url', align: 'left' },
  { name: 'attempts', label: 'Attempts', field: 'attempts', align: 'right' },
  { name: 'body', label: 'Body', field: 'body', align: 'left' },
]

async function load() {
  all.value = await loadQueue()
  pending.value = all.value.filter((r) => r.status !== 'synced' && r.status !== 'dead')
  dead.value = all.value.filter((r) => r.status === 'dead')
}

async function createTest() {
  await enqueue({ entity_kind: 'capture', entity_id: crypto.randomUUID(), url: '/api/proxy/capture/api/capture', method: 'POST', body: { raw: '/task offline queue smoke' } })
  await load()
}

async function drainNow() {
  draining.value = true
  try {
    await drainQueue(async (record) => {
      try {
        const res = await fetch(record.url, { method: record.method, headers: { 'content-type': 'application/json' }, body: record.body ? JSON.stringify(record.body) : undefined })
        return { ok: res.ok, status: res.status }
      } catch (err) {
        return { ok: false, status: 0, error: err instanceof Error ? err.message : String(err) }
      }
    })
    await load()
  } finally {
    draining.value = false
  }
}

async function clear() { await clearSynced(); await load() }
async function retry(id: string) { await retryDeadLetter(id); await load() }
async function discard(id: string) { await removeRecord(id); await load() }

// exposed for potential future badge use; keeps the helper referenced
void deadLetterCount

onMounted(load)
</script>
