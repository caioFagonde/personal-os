<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="hero-panel"><h1>Backup & Restore</h1><p>Create a manifest-backed backup bundle and use it for clone-and-continue drills.</p></section>
    <q-btn color="primary" icon="mdi-archive-arrow-up" label="Create backup manifest" @click="createBackup" />
    <q-btn outline color="primary" icon="mdi-refresh" label="List backups" @click="load" />
    <q-list bordered separator>
      <q-item v-for="b in backups" :key="b.backup_id"><q-item-section><q-item-label>{{ b.backup_id }}</q-item-label><q-item-label caption>{{ b.archive_path }} · {{ b.sha256 }}</q-item-label></q-item-section></q-item>
    </q-list>
    <pre>{{ result }}</pre>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { connectorsUrl, jsonFetch } from '../services/api'
const backups = ref<any[]>([])
const result = ref('')
async function createBackup() { result.value = JSON.stringify(await jsonFetch(`${connectorsUrl}/api/connectors/backup/export`, { method: 'POST', body: JSON.stringify({ include_runtime: false }) }), null, 2); await load() }
async function load() { backups.value = await jsonFetch<any[]>(`${connectorsUrl}/api/connectors/backup/manifests`) }
</script>
