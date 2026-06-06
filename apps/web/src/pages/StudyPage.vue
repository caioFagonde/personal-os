<template>
  <q-page padding>
    <div class="row items-center">
      <div class="col"><h1>Study Engine</h1><p>Reading items, study sessions, and SM-2 flashcards.</p></div>
      <q-btn color="primary" label="Refresh" @click="load" />
    </div>
    <q-card flat bordered class="q-mb-md">
      <q-card-section class="row q-col-gutter-md">
        <q-input class="col-12 col-md-4" v-model="draft.title" label="Title" />
        <q-input class="col-12 col-md-3" v-model="draft.source_ref" label="Source ref" />
        <q-select class="col-12 col-md-2" v-model="draft.kind" :options="kinds" label="Kind" />
        <q-input class="col-12 col-md-1" v-model.number="draft.priority" type="number" label="Priority" />
        <div class="col-12 col-md-2 flex items-end"><q-btn color="primary" label="Add" @click="createItem" /></div>
      </q-card-section>
    </q-card>
    <q-table title="Study queue" :rows="items" :columns="columns" row-key="id" flat bordered>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn dense flat label="Start" @click="patchItem(props.row, { status: 'active', progress: 10 })" />
          <q-btn dense flat label="Done" @click="patchItem(props.row, { status: 'done', progress: 100 })" />
        </q-td>
      </template>
    </q-table>
    <q-banner v-if="error" class="bg-negative text-white q-mt-md">{{ error }}</q-banner>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { deviceKey, jsonFetch, moduleUrl } from '../services/api'
const error = ref('')
const items = ref<any[]>([])
const kinds = ['reading', 'course', 'paper', 'flashcard_set', 'practice', 'project']
const draft = ref({ title: '', source_ref: '', kind: 'reading', priority: 3 })
const columns = [
  { name: 'title', label: 'Title', field: 'title', align: 'left' },
  { name: 'kind', label: 'Kind', field: 'kind' },
  { name: 'status', label: 'Status', field: 'status' },
  { name: 'priority', label: 'Priority', field: 'priority' },
  { name: 'progress', label: 'Progress %', field: 'progress' },
  { name: 'actions', label: 'Actions', field: 'actions' }
]
async function load() {
  error.value = ''
  try { items.value = await jsonFetch<any[]>(`${moduleUrl}/api/study/items`) } catch (e: any) { error.value = e.message }
}
async function createItem() {
  if (!draft.value.title) return
  await jsonFetch(`${moduleUrl}/api/study/items`, { method: 'POST', body: JSON.stringify({ ...draft.value, device_key: deviceKey() }) })
  draft.value.title = ''; draft.value.source_ref = ''
  await load()
}
async function patchItem(row: any, patch: Record<string, any>) {
  await jsonFetch(`${moduleUrl}/api/study/items/${row.id}`, { method: 'PATCH', body: JSON.stringify({ device_key: deviceKey(), ...patch }) })
  await load()
}
onMounted(load)
</script>
