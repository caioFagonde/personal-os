<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Ops" title="Sync Dashboard" subtitle="Round trip, open conflicts, cursors, and local device identity.">
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-4">
        <q-card class="glass-card">
          <q-card-section>
            <div class="metric-card__label">Device</div>
            <div class="text-h5 text-weight-bold">{{ device }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card class="glass-card">
          <q-card-section>
            <div class="metric-card__label">Latest sync id</div>
            <div class="text-h5 text-weight-bold">{{ health.latest_sync_id ?? '---' }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card class="glass-card">
          <q-card-section>
            <div class="metric-card__label">Open conflicts</div>
            <div class="text-h5 text-weight-bold">{{ health.open_conflicts ?? '---' }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div class="row q-gutter-sm">
      <q-btn color="primary" unelevated label="Minimal round trip" icon="mdi-sync" @click="roundTrip" />
      <q-btn outline label="Create manual conflict" icon="mdi-source-branch-sync" @click="makeConflict" />
    </div>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Open conflicts</div>
      </q-card-section>
      <q-table v-if="conflicts.length" :rows="conflicts" :columns="conflictColumns" row-key="id" flat class="nexus-table">
        <template #body-cell-actions="props">
          <q-td :props="props">
            <q-btn dense flat label="Resolve remote" color="primary" size="sm" @click="resolve(props.row)" />
          </q-td>
        </template>
      </q-table>
      <NexusEmptyState v-else icon="mdi-check-circle-outline" message="No open conflicts." hint="All entity versions are in sync." />
    </q-card>

    <q-card v-if="result && Object.keys(result).length" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Last result</div>
        <pre class="code-block">{{ JSON.stringify(result, null, 2) }}</pre>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { deviceKey, jsonFetch, syncUrl } from '../services/api'

const device = deviceKey()
const result = ref<any>({})
const health = ref<any>({})
const conflicts = ref<any[]>([])
const error = ref('')
const loading = ref(false)

const conflictColumns = [
  { name: 'module_id', label: 'Module', field: 'module_id', align: 'left' as const },
  { name: 'entity_type', label: 'Type', field: 'entity_type', align: 'left' as const },
  { name: 'strategy', label: 'Strategy', field: 'strategy', align: 'left' as const },
  { name: 'created_at', label: 'Created', field: 'created_at', align: 'left' as const },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'left' as const }
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [h, c] = await Promise.all([
      jsonFetch(`${syncUrl}/api/sync/health`),
      jsonFetch<any[]>(`${syncUrl}/api/sync/conflicts`),
    ])
    health.value = h
    conflicts.value = c
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function roundTrip() {
  error.value = ''
  try {
    const external_id = `web-${Date.now()}`
    const pushed = await jsonFetch(`${syncUrl}/api/sync/push`, {
      method: 'POST',
      body: JSON.stringify({
        device_key: device,
        changes: [{ module_id: 'study', entity_type: 'study_item', external_id, action: 'create', merge_strategy: 'field_merge', payload: { title: 'Minimal sync round trip', status: 'queued' }, vector_clock: { [device]: 1 } }],
      }),
    })
    const pulled = await jsonFetch(`${syncUrl}/api/sync/pull`, {
      method: 'POST',
      body: JSON.stringify({ device_key: 'another-device', since_id: 0, modules: ['study'] }),
    })
    result.value = { pushed, pulled }
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function makeConflict() {
  error.value = ''
  try {
    const external_id = `conflict-${Date.now()}`
    await jsonFetch(`${syncUrl}/api/sync/push`, {
      method: 'POST',
      body: JSON.stringify({
        device_key: 'phone',
        changes: [{ module_id: 'zettelkasten', entity_type: 'note', external_id, action: 'create', merge_strategy: 'manual', payload: { title: 'Phone version' }, vector_clock: { phone: 1 } }],
      }),
    })
    result.value = await jsonFetch(`${syncUrl}/api/sync/push`, {
      method: 'POST',
      body: JSON.stringify({
        device_key: 'pc',
        changes: [{ module_id: 'zettelkasten', entity_type: 'note', external_id, action: 'update', merge_strategy: 'manual', payload: { title: 'PC version' }, vector_clock: { pc: 1 } }],
      }),
    })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function resolve(row: any) {
  error.value = ''
  try {
    result.value = await jsonFetch(`${syncUrl}/api/sync/conflicts/${row.id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ device_key: device, payload: row.remote_payload, vector_clock: { [device]: Date.now() } }),
    })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(load)
</script>
