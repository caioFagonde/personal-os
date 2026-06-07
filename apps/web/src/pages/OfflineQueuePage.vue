<template>
  <q-page class="column q-gutter-lg">
    <section class="hero-panel">
      <div class="eyebrow">Mobile Continuity</div>
      <h1>Offline Queue</h1>
      <p>Inspect local mutations waiting to sync from mobile/desktop clients.</p>
      <div class="row q-gutter-sm"><q-btn color="primary" label="Refresh" @click="load" /><q-btn color="secondary" label="Create test mutation" @click="createTest" /><q-btn flat label="Clear synced" @click="clear" /></div>
    </section>
    <q-table :rows="rows" :columns="columns" row-key="id" flat bordered class="glass-card">
      <template #body-cell-body="props"><q-td :props="props"><pre class="mini-code">{{ JSON.stringify(props.row.body) }}</pre></q-td></template>
    </q-table>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import type { QTableColumn } from 'quasar'
import { clearSynced, enqueueOfflineMutation, loadOfflineQueue } from '../services/offline-queue'
const rows = ref<any[]>([])
const columns: QTableColumn[] = [
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'method', label: 'Method', field: 'method', align: 'left' },
  { name: 'url', label: 'URL', field: 'url', align: 'left' },
  { name: 'attempts', label: 'Attempts', field: 'attempts', align: 'right' },
  { name: 'body', label: 'Body', field: 'body', align: 'left' }
]
function load(){ rows.value = loadOfflineQueue() }
function createTest(){ enqueueOfflineMutation({ url: '/api/proxy/capture/api/capture', method: 'POST', body: { raw: '/task offline queue smoke' } }); load() }
function clear(){ clearSynced(); load() }
load()
</script>
