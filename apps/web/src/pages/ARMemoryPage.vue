<template>
  <q-page padding>
    <div class="row items-center q-col-gutter-md">
      <div class="col-12 col-md-8">
        <h1>AR Memory Palace</h1>
        <p>Create spatial anchors, project device-orientation reticle taps, and link anchors to notes or geospatial memories.</p>
      </div>
      <div class="col-12 col-md-4 text-right">
        <q-btn color="primary" label="Refresh" @click="load" />
      </div>
    </div>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <q-card bordered flat>
          <q-card-section>
            <div class="text-h6">Create anchor</div>
            <q-input v-model="form.title" label="Title" dense outlined />
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col"><q-input v-model.number="form.local_x" type="number" label="X" dense outlined /></div>
              <div class="col"><q-input v-model.number="form.local_y" type="number" label="Y" dense outlined /></div>
              <div class="col"><q-input v-model.number="form.local_z" type="number" label="Z" dense outlined /></div>
            </div>
            <q-input v-model="form.reference_marker" label="Reference marker" dense outlined class="q-mt-sm" />
          </q-card-section>
          <q-card-actions>
            <q-btn color="primary" label="Create" @click="create" />
          </q-card-actions>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card bordered flat>
          <q-card-section>
            <div class="text-h6">Projection utility</div>
            <div class="row q-col-gutter-sm">
              <div class="col"><q-input v-model.number="projection.alpha" type="number" label="α yaw" dense outlined /></div>
              <div class="col"><q-input v-model.number="projection.beta" type="number" label="β pitch" dense outlined /></div>
              <div class="col"><q-input v-model.number="projection.gamma" type="number" label="γ roll" dense outlined /></div>
              <div class="col"><q-input v-model.number="projection.distance_m" type="number" label="m" dense outlined /></div>
            </div>
            <pre v-if="projected">{{ projected }}</pre>
          </q-card-section>
          <q-card-actions>
            <q-btn color="secondary" label="Project" @click="project" />
            <q-btn flat label="Use result" @click="useProjected" :disable="!projected" />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <q-banner v-if="error" class="bg-negative text-white q-mt-md">{{ error }}</q-banner>

    <h2 class="q-mt-xl">Anchors</h2>
    <q-list bordered separator>
      <q-item v-for="a in anchors" :key="a.id">
        <q-item-section>
          <q-item-label>{{ a.title }}</q-item-label>
          <q-item-label caption>{{ a.anchor_type }} · local({{ a.local_x }}, {{ a.local_y }}, {{ a.local_z }}) · marker {{ a.reference_marker || 'none' }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { jsonFetch, moduleUrl } from '../services/api'

const anchors = ref<any[]>([])
const error = ref('')
const form = ref({ title: '', anchor_type: 'note', local_x: 0, local_y: 0, local_z: -2, reference_marker: '' })
const projection = ref({ alpha: 0, beta: 0, gamma: 0, distance_m: 2 })
const projected = ref<any>(null)

async function load() {
  try { anchors.value = await jsonFetch<any[]>(`${moduleUrl}/api/ar/anchors`) } catch (e: any) { error.value = e.message }
}
async function create() {
  error.value = ''
  try {
    await jsonFetch<any>(`${moduleUrl}/api/ar/anchors`, { method: 'POST', body: JSON.stringify(form.value) })
    form.value.title = ''
    await load()
  } catch (e: any) { error.value = e.message }
}
async function project() {
  try { projected.value = await jsonFetch<any>(`${moduleUrl}/api/ar/project`, { method: 'POST', body: JSON.stringify(projection.value) }) } catch (e: any) { error.value = e.message }
}
function useProjected() {
  if (!projected.value) return
  form.value.local_x = projected.value.local_x
  form.value.local_y = projected.value.local_y
  form.value.local_z = projected.value.local_z
}
onMounted(load)
</script>
