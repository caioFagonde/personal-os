<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Field" title="Geospatial Memory" subtitle="POIs, field notes, anchors, and nearby queries through PostGIS.">
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Add memory</div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-3">
            <q-input v-model="draft.title" outlined label="Title" />
          </div>
          <div class="col-12 col-md-2">
            <q-input v-model.number="draft.latitude" outlined type="number" label="Latitude" />
          </div>
          <div class="col-12 col-md-2">
            <q-input v-model.number="draft.longitude" outlined type="number" label="Longitude" />
          </div>
          <div class="col-12 col-md-2">
            <q-select v-model="draft.memory_type" outlined :options="types" label="Type" />
          </div>
          <div class="col-12 col-md-2">
            <q-input v-model="tagText" outlined label="Tags" />
          </div>
          <div class="col-12 col-md-1 flex items-end">
            <q-btn color="primary" unelevated icon="mdi-plus" label="Add" :loading="creating" @click="createMemory" />
          </div>
          <div class="col-12">
            <q-input v-model="draft.description" outlined label="Description" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Memories</div>
      </q-card-section>
      <q-card-section v-if="loading && !memories.length">
        <q-inner-loading showing color="primary" />
      </q-card-section>
      <q-table v-else-if="memories.length" :rows="memories" :columns="columns" row-key="id" flat class="nexus-table" />
      <NexusEmptyState v-else icon="mdi-map-marker-outline" message="No geospatial memories yet." hint="Add a POI, route, or field note above." />
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { QTableColumn } from 'quasar'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { deviceKey, jsonFetch, moduleUrl } from '../services/api'

const error = ref('')
const loading = ref(false)
const creating = ref(false)
const memories = ref<any[]>([])
const tagText = ref('')
const types = ['poi', 'route', 'area', 'field_note', 'anchor']
const draft = ref({ title: '', description: '', latitude: -23.5505, longitude: -46.6333, memory_type: 'poi' })
const columns: QTableColumn[] = [
  { name: 'title', label: 'Title', field: 'title', align: 'left' },
  { name: 'memory_type', label: 'Type', field: 'memory_type' },
  { name: 'latitude', label: 'Lat', field: 'latitude' },
  { name: 'longitude', label: 'Lng', field: 'longitude' },
  { name: 'tags', label: 'Tags', field: (r: any) => (r.tags || []).join(', ') }
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    memories.value = await jsonFetch<any[]>(`${moduleUrl}/api/geospatial/memories`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function createMemory() {
  if (!draft.value.title.trim()) return
  creating.value = true
  error.value = ''
  try {
    await jsonFetch(`${moduleUrl}/api/geospatial/memories`, {
      method: 'POST',
      body: JSON.stringify({
        ...draft.value,
        device_key: deviceKey(),
        tags: tagText.value.split(',').map(s => s.trim()).filter(Boolean),
      }),
    })
    draft.value.title = ''
    draft.value.description = ''
    tagText.value = ''
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>
