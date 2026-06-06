<template>
  <q-page padding>
    <div class="row items-center"><div class="col"><h1>Zettelkasten</h1><p>Markdown notes, backlinks, tags, and Obsidian export.</p></div><q-btn label="Refresh" color="primary" @click="load" /></div>
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <q-input v-model="draft.title" label="Title" class="q-mb-sm" />
        <q-input v-model="draft.body" label="Body" type="textarea" autogrow hint="Use [[Note Title]] to create backlinks." />
        <q-input v-model="tagText" label="Tags, comma-separated" class="q-mt-sm" />
        <q-btn class="q-mt-md" color="primary" label="Create note" @click="createNote" />
      </q-card-section>
    </q-card>
    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-4" v-for="note in notes" :key="note.id">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-h6">{{ note.title }}</div>
            <div class="text-caption">{{ note.note_type }} · {{ note.slug }}</div>
            <q-chip dense v-for="tag in note.tags" :key="tag">{{ tag }}</q-chip>
            <p class="ellipsis-3-lines">{{ note.body }}</p>
          </q-card-section>
          <q-card-actions>
            <q-btn flat label="Open" @click="openNote(note.id)" />
            <q-btn flat label="Export" @click="exportNote(note.id)" />
          </q-card-actions>
        </q-card>
      </div>
    </div>
    <q-dialog v-model="dialog"><q-card style="min-width: 70vw"><q-card-section><pre>{{ selected }}</pre></q-card-section></q-card></q-dialog>
    <q-banner v-if="error" class="bg-negative text-white q-mt-md">{{ error }}</q-banner>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { deviceKey, jsonFetch, moduleUrl } from '../services/api'
const notes = ref<any[]>([]); const error = ref(''); const selected = ref<any>({}); const dialog = ref(false)
const tagText = ref('')
const draft = ref({ title: '', body: '', note_type: 'permanent' })
async function load() { try { notes.value = await jsonFetch<any[]>(`${moduleUrl}/api/zettelkasten/notes`); error.value = '' } catch (e: any) { error.value = e.message } }
async function createNote() {
  await jsonFetch(`${moduleUrl}/api/zettelkasten/notes`, { method: 'POST', body: JSON.stringify({ ...draft.value, device_key: deviceKey(), tags: tagText.value.split(',').map(s => s.trim()).filter(Boolean) }) })
  draft.value.title = ''; draft.value.body = ''; tagText.value = ''; await load()
}
async function openNote(id: string) { selected.value = await jsonFetch(`${moduleUrl}/api/zettelkasten/notes/${id}`); dialog.value = true }
async function exportNote(id: string) { selected.value = await jsonFetch(`${moduleUrl}/api/zettelkasten/notes/${id}/obsidian`); dialog.value = true }
onMounted(load)
</script>
