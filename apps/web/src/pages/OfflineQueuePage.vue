<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Mobile Continuity" title="Offline Queue" subtitle="Inspect local mutations waiting to sync from mobile/desktop clients.">
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh" @click="load" />
        <q-btn color="secondary" icon="mdi-plus" label="Create test mutation" @click="createTest" />
        <q-btn outline label="Clear synced" @click="clear" />
      </template>
    </NexusPageHero>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Queue ({{ rows.length }} items)</div>
      </q-card-section>
      <q-table v-if="rows.length" :rows="rows" :columns="columns" row-key="id" flat class="nexus-table">
        <template #body-cell-body="props">
          <q-td :props="props">
            <pre class="mini-code">{{ JSON.stringify(props.row.body) }}</pre>
          </q-td>
        </template>
      </q-table>
      <NexusEmptyState v-else icon="mdi-cloud-check-outline" message="Offline queue is empty." hint="All mutations have been synced." />
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import type { QTableColumn } from 'quasar'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { clearSynced, enqueueOfflineMutation, loadOfflineQueue } from '../services/offline-queue'

const rows = ref<any[]>([])
const columns: QTableColumn[] = [
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'method', label: 'Method', field: 'method', align: 'left' },
  { name: 'url', label: 'URL', field: 'url', align: 'left' },
  { name: 'attempts', label: 'Attempts', field: 'attempts', align: 'right' },
  { name: 'body', label: 'Body', field: 'body', align: 'left' }
]

function load() { rows.value = loadOfflineQueue() }
function createTest() {
  enqueueOfflineMutation({ url: '/api/proxy/capture/api/capture', method: 'POST', body: { raw: '/task offline queue smoke' } })
  load()
}
function clear() { clearSynced(); load() }
load()
</script>
