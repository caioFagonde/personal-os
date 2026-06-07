<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Growth" title="Study Engine" subtitle="Reading items, study sessions, and SM-2 flashcards.">
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
        <div class="text-h6 q-mb-sm">Add study item</div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-4">
            <q-input v-model="draft.title" outlined label="Title" />
          </div>
          <div class="col-12 col-md-3">
            <q-input v-model="draft.source_ref" outlined label="Source ref" />
          </div>
          <div class="col-12 col-md-2">
            <q-select v-model="draft.kind" outlined :options="kinds" label="Kind" />
          </div>
          <div class="col-12 col-md-1">
            <q-input v-model.number="draft.priority" outlined type="number" label="Priority" />
          </div>
          <div class="col-12 col-md-2 flex items-end">
            <q-btn color="primary" unelevated label="Add" icon="mdi-plus" :loading="creating" @click="createItem" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Study queue</div>
      </q-card-section>
      <q-card-section v-if="loading && !items.length">
        <q-inner-loading showing color="primary" />
      </q-card-section>
      <q-table v-else-if="items.length" :rows="items" :columns="columns" row-key="id" flat class="nexus-table">
        <template #body-cell-actions="props">
          <q-td :props="props">
            <q-btn dense flat label="Start" color="primary" size="sm" @click="patchItem(props.row, { status: 'active', progress: 10 })" />
            <q-btn dense flat label="Done" color="positive" size="sm" @click="patchItem(props.row, { status: 'done', progress: 100 })" />
          </q-td>
        </template>
      </q-table>
      <NexusEmptyState v-else icon="mdi-book-open-outline" message="No study items yet." hint="Add a reading, course, or flashcard set above." />
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
const items = ref<any[]>([])
const loading = ref(false)
const creating = ref(false)
const kinds = ['reading', 'course', 'paper', 'flashcard_set', 'practice', 'project']
const draft = ref({ title: '', source_ref: '', kind: 'reading', priority: 3 })
const columns: QTableColumn[] = [
  { name: 'title', label: 'Title', field: 'title', align: 'left' },
  { name: 'kind', label: 'Kind', field: 'kind' },
  { name: 'status', label: 'Status', field: 'status' },
  { name: 'priority', label: 'Priority', field: 'priority' },
  { name: 'progress', label: 'Progress %', field: 'progress' },
  { name: 'actions', label: 'Actions', field: 'actions' }
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = await jsonFetch<any[]>(`${moduleUrl}/api/study/items`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function createItem() {
  if (!draft.value.title) return
  creating.value = true
  error.value = ''
  try {
    await jsonFetch(`${moduleUrl}/api/study/items`, {
      method: 'POST',
      body: JSON.stringify({ ...draft.value, device_key: deviceKey() }),
    })
    draft.value.title = ''
    draft.value.source_ref = ''
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    creating.value = false
  }
}

async function patchItem(row: any, patch: Record<string, any>) {
  error.value = ''
  try {
    await jsonFetch(`${moduleUrl}/api/study/items/${row.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ device_key: deviceKey(), ...patch }),
    })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(load)
</script>
