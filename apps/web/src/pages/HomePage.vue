<template>
  <q-page padding>
    <div class="row items-center q-col-gutter-md">
      <div class="col-12 col-md-8">
        <h1>Nexus Core</h1>
        <p>Control plane shell for local-first specialized modules.</p>
      </div>
      <div class="col-12 col-md-4 text-right">
        <q-btn color="primary" label="Refresh" @click="load" />
      </div>
    </div>

    <div class="row q-col-gutter-md q-mt-md">
      <div class="col-12 col-md-3" v-for="card in healthCards" :key="card.label">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-overline">{{ card.label }}</div>
            <div class="text-h5">{{ card.value }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <h2 class="q-mt-xl">Installed modules</h2>
    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-4" v-for="m in modules" :key="m.id">
        <q-card bordered flat>
          <q-card-section>
            <div class="text-h6">{{ m.name }}</div>
            <div class="text-caption">{{ m.id }} · {{ m.version }} · {{ m.health }}</div>
            <q-chip dense v-for="p in m.permissions" :key="p">{{ p }}</q-chip>
          </q-card-section>
          <q-card-actions>
            <q-btn flat color="primary" :to="m.routes?.web || `/modules/${m.id}`" label="Open" />
          </q-card-actions>
        </q-card>
      </div>
    </div>
    <q-banner v-if="error" class="bg-negative text-white q-mt-md">{{ error }}</q-banner>
  </q-page>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiUrl, jsonFetch, syncUrl, commandUrl, moduleUrl } from '../services/api'
const modules = ref<any[]>([])
const health = ref<Record<string, any>>({})
const error = ref('')
const healthCards = computed(() => [
  { label: 'Modules', value: modules.value.length },
  { label: 'API', value: health.value.api?.status || 'unknown' },
  { label: 'Sync', value: health.value.sync?.status || 'unknown' },
  { label: 'Module API', value: health.value.modules?.status || 'unknown' }
])
async function load() {
  error.value = ''
  try {
    const [apiHealth, syncHealth, moduleHealth, mods] = await Promise.all([
      jsonFetch<any>(`${apiUrl}/health`),
      jsonFetch<any>(`${syncUrl}/api/sync/health`),
      jsonFetch<any>(`${moduleUrl}/health`),
      jsonFetch<any[]>(`${apiUrl}/api/modules`)
    ])
    health.value = { api: apiHealth, sync: syncHealth, modules: moduleHealth, command: commandUrl }
    modules.value = mods
  } catch (e: any) { error.value = e.message }
}
onMounted(load)
</script>
