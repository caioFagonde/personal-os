<template>
  <q-page class="column q-gutter-lg">
    <section class="hero-panel">
      <div class="eyebrow">Sync Safety</div>
      <h1>Conflict Resolution</h1>
      <p>Inspect divergent entity versions and commit an explicit resolution.</p>
      <q-btn color="primary" icon="mdi-refresh" label="Load conflicts" @click="load" />
    </section>
    <q-card v-for="c in conflicts" :key="c.id" class="glass-card">
      <q-card-section>
        <div class="row justify-between items-center">
          <div><div class="text-h6">{{ c.module_id }} · {{ c.entity_type }}</div><div class="text-caption">{{ c.id }}</div></div>
          <q-badge color="warning">{{ c.status }}</q-badge>
        </div>
        <div class="row q-col-gutter-md q-mt-md">
          <div class="col-12 col-md-6"><div class="text-subtitle2">Local</div><pre class="code-block">{{ JSON.stringify(c.local_payload, null, 2) }}</pre></div>
          <div class="col-12 col-md-6"><div class="text-subtitle2">Remote</div><pre class="code-block">{{ JSON.stringify(c.remote_payload, null, 2) }}</pre></div>
        </div>
        <q-input v-model="drafts[c.id]" type="textarea" autogrow label="Resolved JSON payload" class="q-mt-md" />
        <div class="row q-gutter-sm q-mt-md">
          <q-btn color="primary" label="Use local" @click="drafts[c.id] = JSON.stringify(c.local_payload, null, 2)" />
          <q-btn color="secondary" label="Use remote" @click="drafts[c.id] = JSON.stringify(c.remote_payload, null, 2)" />
          <q-btn color="positive" label="Commit resolution" @click="resolve(c.id)" />
        </div>
      </q-card-section>
    </q-card>
    <q-banner v-if="!conflicts.length" class="glass-card">No open conflicts.</q-banner>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { jsonFetch, syncUrl, deviceKey } from '../services/api'
const conflicts = ref<any[]>([])
const drafts = reactive<Record<string, string>>({})
async function load() {
  conflicts.value = await jsonFetch(`${syncUrl}/api/sync/conflicts`)
  for (const c of conflicts.value) drafts[c.id] ||= JSON.stringify(c.remote_payload ?? c.local_payload ?? {}, null, 2)
}
async function resolve(id: string) {
  const payload = JSON.parse(drafts[id] || '{}')
  await jsonFetch(`${syncUrl}/api/sync/conflicts/${id}/resolve`, { method: 'POST', body: JSON.stringify({ device_key: deviceKey(), payload, vector_clock: { [deviceKey()]: Date.now() } }) })
  await load()
}
onMounted(load)
</script>
