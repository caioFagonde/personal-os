<template>
  <q-page padding>
    <div class="row items-center"><div class="col"><h1>Sync Dashboard</h1><p>Round trip, open conflicts, cursors, and local device identity.</p></div><q-btn label="Refresh" color="primary" @click="load" /></div>
    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-md-4"><q-card flat bordered><q-card-section><div class="text-overline">Device</div><div class="text-body2">{{ device }}</div></q-card-section></q-card></div>
      <div class="col-12 col-md-4"><q-card flat bordered><q-card-section><div class="text-overline">Latest sync id</div><div class="text-h5">{{ health.latest_sync_id ?? '—' }}</div></q-card-section></q-card></div>
      <div class="col-12 col-md-4"><q-card flat bordered><q-card-section><div class="text-overline">Open conflicts</div><div class="text-h5">{{ health.open_conflicts ?? '—' }}</div></q-card-section></q-card></div>
    </div>
    <q-btn color="primary" label="Minimal round trip" @click="roundTrip" />
    <q-btn class="q-ml-sm" label="Create manual conflict" @click="makeConflict" />
    <h2>Open conflicts</h2>
    <q-table :rows="conflicts" :columns="conflictColumns" row-key="id" flat bordered>
      <template #body-cell-actions="props"><q-td :props="props"><q-btn dense flat label="Resolve remote" @click="resolve(props.row)" /></q-td></template>
    </q-table>
    <h2>Last result</h2><pre>{{ result }}</pre>
    <q-banner v-if="error" class="bg-negative text-white q-mt-md">{{ error }}</q-banner>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { deviceKey, jsonFetch, syncUrl } from '../services/api'
const device = deviceKey(); const result = ref<any>({}); const health = ref<any>({}); const conflicts = ref<any[]>([]); const error = ref('')
const conflictColumns = [
  { name: 'module_id', label: 'Module', field: 'module_id' },
  { name: 'entity_type', label: 'Type', field: 'entity_type' },
  { name: 'strategy', label: 'Strategy', field: 'strategy' },
  { name: 'created_at', label: 'Created', field: 'created_at' },
  { name: 'actions', label: 'Actions', field: 'actions' }
]
async function load() {
  try { health.value = await jsonFetch(`${syncUrl}/api/sync/health`); conflicts.value = await jsonFetch(`${syncUrl}/api/sync/conflicts`); error.value = '' } catch (e: any) { error.value = e.message }
}
async function roundTrip() {
  const external_id = `web-${Date.now()}`
  const pushed = await jsonFetch(`${syncUrl}/api/sync/push`, { method: 'POST', body: JSON.stringify({ device_key: device, changes: [{ module_id: 'study', entity_type: 'study_item', external_id, action: 'create', merge_strategy: 'field_merge', payload: { title: 'Minimal sync round trip', status: 'queued' }, vector_clock: { [device]: 1 } }] }) })
  const pulled = await jsonFetch(`${syncUrl}/api/sync/pull`, { method: 'POST', body: JSON.stringify({ device_key: 'another-device', since_id: 0, modules: ['study'] }) })
  result.value = { pushed, pulled }; await load()
}
async function makeConflict() {
  const external_id = `conflict-${Date.now()}`
  await jsonFetch(`${syncUrl}/api/sync/push`, { method: 'POST', body: JSON.stringify({ device_key: 'phone', changes: [{ module_id: 'zettelkasten', entity_type: 'note', external_id, action: 'create', merge_strategy: 'manual', payload: { title: 'Phone version' }, vector_clock: { phone: 1 } }] }) })
  result.value = await jsonFetch(`${syncUrl}/api/sync/push`, { method: 'POST', body: JSON.stringify({ device_key: 'pc', changes: [{ module_id: 'zettelkasten', entity_type: 'note', external_id, action: 'update', merge_strategy: 'manual', payload: { title: 'PC version' }, vector_clock: { pc: 1 } }] }) })
  await load()
}
async function resolve(row: any) {
  result.value = await jsonFetch(`${syncUrl}/api/sync/conflicts/${row.id}/resolve`, { method: 'POST', body: JSON.stringify({ device_key: device, payload: row.remote_payload, vector_clock: { [device]: Date.now() } }) })
  await load()
}
onMounted(load)
</script>
