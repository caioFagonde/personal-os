<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Field" title="AR Memory Palace" subtitle="Create spatial anchors, project device-orientation reticle taps, and link anchors to notes or geospatial memories.">
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
        <div class="text-h6 q-mb-sm">Device capabilities</div>
        <div class="row q-col-gutter-sm">
          <div class="col-auto">
            <q-chip
              :color="capColor(geoCap)"
              text-color="white"
              :icon="capIcon(geoCap)"
            >
              Geolocation: {{ capLabel(geoCap) }}
            </q-chip>
          </div>
          <div class="col-auto">
            <q-chip
              :color="capColor(orientationCap)"
              text-color="white"
              :icon="capIcon(orientationCap)"
            >
              Orientation: {{ capLabel(orientationCap) }}
            </q-chip>
          </div>
          <div class="col-auto">
            <q-chip
              :color="capColor(motionCap)"
              text-color="white"
              :icon="capIcon(motionCap)"
            >
              Motion: {{ capLabel(motionCap) }}
            </q-chip>
          </div>
        </div>
        <div v-if="geoCap === 'denied' || orientationCap === 'denied'" class="q-mt-sm text-caption text-grey-6">
          Some permissions were denied. Check your browser settings to allow location and sensor access, then reload.
        </div>
        <div v-if="geoCap === 'unsupported' || orientationCap === 'unsupported'" class="q-mt-sm text-caption text-grey-6">
          Some sensors are not available on this device. AR features may be limited.
        </div>
      </q-card-section>
    </q-card>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Create anchor</div>
            <q-input v-model="form.title" outlined label="Title" />
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col"><q-input v-model.number="form.local_x" outlined type="number" label="X" /></div>
              <div class="col"><q-input v-model.number="form.local_y" outlined type="number" label="Y" /></div>
              <div class="col"><q-input v-model.number="form.local_z" outlined type="number" label="Z" /></div>
            </div>
            <q-input v-model="form.reference_marker" outlined label="Reference marker" class="q-mt-sm" />
          </q-card-section>
          <q-card-actions>
            <q-btn color="primary" unelevated label="Create" icon="mdi-plus" :loading="creatingAnchor" @click="create" />
          </q-card-actions>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Projection utility</div>
            <div class="row q-col-gutter-sm">
              <div class="col"><q-input v-model.number="projection.alpha" outlined type="number" label="a yaw" /></div>
              <div class="col"><q-input v-model.number="projection.beta" outlined type="number" label="b pitch" /></div>
              <div class="col"><q-input v-model.number="projection.gamma" outlined type="number" label="g roll" /></div>
              <div class="col"><q-input v-model.number="projection.distance_m" outlined type="number" label="m" /></div>
            </div>
            <pre v-if="projected" class="code-block q-mt-sm">{{ JSON.stringify(projected, null, 2) }}</pre>
          </q-card-section>
          <q-card-actions>
            <q-btn color="secondary" unelevated label="Project" @click="project" />
            <q-btn flat color="primary" label="Use result" @click="useProjected" :disable="!projected" />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Anchors</div>
      </q-card-section>
      <q-list v-if="anchors.length" separator>
        <q-item v-for="a in anchors" :key="a.id">
          <q-item-section avatar>
            <q-icon name="mdi-cube-scan" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ a.title }}</q-item-label>
            <q-item-label caption>{{ a.anchor_type }} · local({{ a.local_x }}, {{ a.local_y }}, {{ a.local_z }}) · marker {{ a.reference_marker || 'none' }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
      <NexusEmptyState v-else icon="mdi-cube-scan" message="No anchors yet." hint="Create a spatial anchor above." />
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { jsonFetch, moduleUrl } from '../services/api'

type CapState = 'checking' | 'available' | 'denied' | 'unsupported'

const anchors = ref<any[]>([])
const error = ref('')
const loading = ref(false)
const creatingAnchor = ref(false)
const form = ref({ title: '', anchor_type: 'note', local_x: 0, local_y: 0, local_z: -2, reference_marker: '' })
const projection = ref({ alpha: 0, beta: 0, gamma: 0, distance_m: 2 })
const projected = ref<any>(null)

const geoCap = ref<CapState>('checking')
const orientationCap = ref<CapState>('checking')
const motionCap = ref<CapState>('checking')

function capColor(state: CapState): string {
  switch (state) {
    case 'available': return 'positive'
    case 'denied': return 'negative'
    case 'unsupported': return 'grey'
    default: return 'grey-5'
  }
}

function capIcon(state: CapState): string {
  switch (state) {
    case 'available': return 'mdi-check-circle'
    case 'denied': return 'mdi-cancel'
    case 'unsupported': return 'mdi-help-circle'
    default: return 'mdi-loading'
  }
}

function capLabel(state: CapState): string {
  switch (state) {
    case 'available': return 'Available'
    case 'denied': return 'Denied'
    case 'unsupported': return 'Unsupported'
    default: return 'Checking...'
  }
}

function detectCapabilities() {
  if (!navigator.geolocation) {
    geoCap.value = 'unsupported'
  } else {
    navigator.permissions?.query({ name: 'geolocation' }).then(result => {
      if (result.state === 'granted') geoCap.value = 'available'
      else if (result.state === 'denied') geoCap.value = 'denied'
      else geoCap.value = 'available'
      result.addEventListener('change', () => {
        geoCap.value = result.state === 'granted' ? 'available'
          : result.state === 'denied' ? 'denied' : 'available'
      })
    }).catch(() => {
      geoCap.value = 'available'
    })
  }

  if (!('DeviceOrientationEvent' in window)) {
    orientationCap.value = 'unsupported'
  } else if (typeof (DeviceOrientationEvent as any).requestPermission === 'function') {
    orientationCap.value = 'available'
  } else {
    orientationCap.value = 'available'
  }

  if (!('DeviceMotionEvent' in window)) {
    motionCap.value = 'unsupported'
  } else if (typeof (DeviceMotionEvent as any).requestPermission === 'function') {
    motionCap.value = 'available'
  } else {
    motionCap.value = 'available'
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    anchors.value = await jsonFetch<any[]>(`${moduleUrl}/api/ar/anchors`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.value.title.trim()) return
  creatingAnchor.value = true
  error.value = ''
  try {
    await jsonFetch<any>(`${moduleUrl}/api/ar/anchors`, {
      method: 'POST',
      body: JSON.stringify(form.value),
    })
    form.value.title = ''
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    creatingAnchor.value = false
  }
}

async function project() {
  error.value = ''
  try {
    projected.value = await jsonFetch<any>(`${moduleUrl}/api/ar/project`, {
      method: 'POST',
      body: JSON.stringify(projection.value),
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

function useProjected() {
  if (!projected.value) return
  form.value.local_x = projected.value.local_x
  form.value.local_y = projected.value.local_y
  form.value.local_z = projected.value.local_z
}

onMounted(() => {
  load()
  detectCapabilities()
})
</script>
