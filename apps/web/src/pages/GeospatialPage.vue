<template>
  <q-page padding>
    <div class="row items-center"><div class="col"><h1>Geospatial Memory</h1><p>POIs, field notes, anchors, and nearby queries through PostGIS.</p></div><q-btn label="Refresh" color="primary" @click="load" /></div>
    <q-card flat bordered class="q-mb-md"><q-card-section class="row q-col-gutter-md">
      <q-input class="col-12 col-md-3" v-model="draft.title" label="Title" />
      <q-input class="col-12 col-md-2" v-model.number="draft.latitude" type="number" label="Latitude" />
      <q-input class="col-12 col-md-2" v-model.number="draft.longitude" type="number" label="Longitude" />
      <q-select class="col-12 col-md-2" v-model="draft.memory_type" :options="types" label="Type" />
      <q-input class="col-12 col-md-2" v-model="tagText" label="Tags" />
      <div class="col-12 col-md-1 flex items-end"><q-btn color="primary" label="Add" @click="createMemory" /></div>
      <q-input class="col-12" v-model="draft.description" label="Description" />
    </q-card-section></q-card>
    <q-table :rows="memories" :columns="columns" row-key="id" flat bordered />
    <q-banner v-if="error" class="bg-negative text-white q-mt-md">{{ error }}</q-banner>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { QTableColumn } from 'quasar'
import { deviceKey, jsonFetch, moduleUrl } from '../services/api'
const error = ref(''); const memories = ref<any[]>([]); const tagText = ref('')
const types = ['poi', 'route', 'area', 'field_note', 'anchor']
const draft = ref({ title: '', description: '', latitude: -23.5505, longitude: -46.6333, memory_type: 'poi' })
const columns: QTableColumn[] = [
  { name: 'title', label: 'Title', field: 'title', align: 'left' },
  { name: 'memory_type', label: 'Type', field: 'memory_type' },
  { name: 'latitude', label: 'Lat', field: 'latitude' },
  { name: 'longitude', label: 'Lng', field: 'longitude' },
  { name: 'tags', label: 'Tags', field: (r: any) => (r.tags || []).join(', ') }
]
async function load() { try { memories.value = await jsonFetch<any[]>(`${moduleUrl}/api/geospatial/memories`); error.value = '' } catch (e: any) { error.value = e.message } }
async function createMemory() {
  await jsonFetch(`${moduleUrl}/api/geospatial/memories`, { method: 'POST', body: JSON.stringify({ ...draft.value, device_key: deviceKey(), tags: tagText.value.split(',').map(s => s.trim()).filter(Boolean) }) })
  draft.value.title = ''; draft.value.description = ''; tagText.value = ''; await load()
}
onMounted(load)
</script>
