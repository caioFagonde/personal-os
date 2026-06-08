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

    <q-banner v-if="tileStatus === 'unavailable'" class="bg-warning text-dark" rounded>
      <template #avatar><q-icon name="mdi-map-marker-off" /></template>
      <div>
        <strong>Map tile server not available.</strong>
        No tile datasets are registered or the tile server is unreachable.
      </div>
      <div class="q-mt-xs text-caption">
        To set up local map tiles:
        <ol class="q-ma-none q-pl-md">
          <li>Download an .mbtiles file for your region (e.g. from OpenMapTiles)</li>
          <li>Place it in the <code>data/tiles/</code> directory</li>
          <li>Run <code>./scripts/maps/register-mbtiles.sh</code></li>
          <li>Restart the tile-server container</li>
        </ol>
      </div>
      <template #action>
        <q-btn flat color="dark" label="Retry" icon="mdi-refresh" @click="checkTileServer" />
      </template>
    </q-banner>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Add memory</div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-3">
            <q-input v-model="draft.title" outlined label="Title" />
          </div>
          <div class="col-12 col-md-2">
            <q-input
              v-model.number="draft.latitude"
              outlined
              type="number"
              label="Latitude"
              :rules="[latRule]"
              :error="latError !== ''"
              :error-message="latError"
              @update:model-value="latError = ''"
            />
          </div>
          <div class="col-12 col-md-2">
            <q-input
              v-model.number="draft.longitude"
              outlined
              type="number"
              label="Longitude"
              :rules="[lngRule]"
              :error="lngError !== ''"
              :error-message="lngError"
              @update:model-value="lngError = ''"
            />
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
            <div class="row q-col-gutter-sm items-center">
              <div class="col">
                <q-input v-model="draft.description" outlined label="Description" />
              </div>
              <div class="col-auto">
                <q-btn
                  color="secondary"
                  unelevated
                  icon="mdi-crosshairs-gps"
                  label="Use current location"
                  :loading="locating"
                  :disable="geoState === 'denied'"
                  @click="useCurrentLocation"
                />
              </div>
            </div>
            <div v-if="geoState === 'denied'" class="q-mt-sm">
              <q-banner class="bg-orange-2 text-dark" rounded dense>
                <template #avatar><q-icon name="mdi-map-marker-alert" color="orange" /></template>
                Location permission denied. Enter coordinates manually above, or allow location access in your browser settings and reload.
              </q-banner>
            </div>
            <div v-if="geoState === 'unsupported'" class="q-mt-sm">
              <q-banner class="bg-grey-3 text-dark" rounded dense>
                <template #avatar><q-icon name="mdi-map-marker-question" color="grey" /></template>
                Geolocation is not available in this browser. Enter coordinates manually.
              </q-banner>
            </div>
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
const locating = ref(false)
const memories = ref<any[]>([])
const tagText = ref('')
const types = ['poi', 'route', 'area', 'field_note', 'anchor']
const draft = ref({ title: '', description: '', latitude: -23.5505, longitude: -46.6333, memory_type: 'poi' })
const latError = ref('')
const lngError = ref('')

type GeoState = 'unknown' | 'granted' | 'denied' | 'unsupported'
const geoState = ref<GeoState>('unknown')

type TileStatus = 'unknown' | 'available' | 'unavailable'
const tileStatus = ref<TileStatus>('unknown')

const columns: QTableColumn[] = [
  { name: 'title', label: 'Title', field: 'title', align: 'left' },
  { name: 'memory_type', label: 'Type', field: 'memory_type' },
  { name: 'latitude', label: 'Lat', field: 'latitude' },
  { name: 'longitude', label: 'Lng', field: 'longitude' },
  { name: 'tags', label: 'Tags', field: (r: any) => (r.tags || []).join(', ') }
]

function isValidLat(v: number): boolean {
  return typeof v === 'number' && isFinite(v) && v >= -90 && v <= 90
}

function isValidLng(v: number): boolean {
  return typeof v === 'number' && isFinite(v) && v >= -180 && v <= 180
}

function latRule(v: number): boolean | string {
  return isValidLat(v) || 'Latitude must be between -90 and 90'
}

function lngRule(v: number): boolean | string {
  return isValidLng(v) || 'Longitude must be between -180 and 180'
}

function useCurrentLocation() {
  if (!navigator.geolocation) {
    geoState.value = 'unsupported'
    return
  }
  locating.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      draft.value.latitude = Math.round(pos.coords.latitude * 1e6) / 1e6
      draft.value.longitude = Math.round(pos.coords.longitude * 1e6) / 1e6
      geoState.value = 'granted'
      locating.value = false
    },
    (err) => {
      locating.value = false
      if (err.code === err.PERMISSION_DENIED) {
        geoState.value = 'denied'
      } else {
        error.value = `Geolocation error: ${err.message}`
      }
    },
    { enableHighAccuracy: true, timeout: 10000 }
  )
}

async function checkTileServer() {
  try {
    const datasets = await jsonFetch<any[]>(`${moduleUrl}/api/geospatial/map-datasets`)
    tileStatus.value = datasets.length > 0 ? 'available' : 'unavailable'
  } catch {
    tileStatus.value = 'unavailable'
  }
}

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
  if (!isValidLat(draft.value.latitude)) {
    latError.value = 'Latitude must be between -90 and 90'
    return
  }
  if (!isValidLng(draft.value.longitude)) {
    lngError.value = 'Longitude must be between -180 and 180'
    return
  }
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

onMounted(() => {
  load()
  checkTileServer()
})
</script>
