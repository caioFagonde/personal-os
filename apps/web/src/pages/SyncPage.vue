<template>
  <q-page padding>
    <h1>Sync Health</h1>
    <q-btn label="Minimal round trip" @click="roundTrip" />
    <pre>{{ result }}</pre>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
const result = ref({})
async function roundTrip() {
  const sync = import.meta.env.VITE_SYNC_URL || 'http://localhost:8081'
  const change = {
    device_key: 'web-dev',
    changes: [{
      module_id: 'study',
      entity_type: 'study_item',
      external_id: `web-${Date.now()}`,
      action: 'create',
      merge_strategy: 'lww',
      payload: { title: 'Minimal sync round trip', status: 'queued' },
      vector_clock: { 'web-dev': 1 }
    }]
  }
  const pushed = await fetch(`${sync}/api/sync/push`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(change) }).then(r => r.json())
  const pulled = await fetch(`${sync}/api/sync/pull`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ device_key: 'another-device', since_id: 0, modules: ['study'] }) }).then(r => r.json())
  result.value = { pushed, pulled }
}
</script>
