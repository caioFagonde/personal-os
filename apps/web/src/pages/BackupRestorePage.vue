<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="hero-panel"><div class="eyebrow">Continuity</div><h1>Backup & Restore</h1><p>Create local backups and upload encrypted bundles to Google Drive or OneDrive once OAuth is connected.</p></section>
    <div class="row q-gutter-sm">
      <q-btn color="primary" icon="mdi-archive-arrow-up" label="Create local backup" @click="createBackup" />
      <q-btn color="secondary" icon="mdi-google-drive" label="Upload to Google Drive" @click="upload('google')" />
      <q-btn color="secondary" icon="mdi-microsoft-onedrive" label="Upload to OneDrive" @click="upload('microsoft')" />
      <q-btn outline color="primary" icon="mdi-refresh" label="List backups" @click="load" />
    </div>
    <q-list bordered separator class="glass-card">
      <q-item v-for="b in backups" :key="b.backup_id">
        <q-item-section><q-item-label>{{ b.backup_id }}</q-item-label><q-item-label caption>{{ b.archive_path }} · {{ b.sha256 }}</q-item-label><q-item-label v-if="b.remote_uri" caption>Remote: {{ b.remote_uri }}</q-item-label></q-item-section>
      </q-item>
    </q-list>
    <pre class="code-block">{{ result }}</pre>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { connectorsUrl, jsonFetch } from '../services/api'
const backups = ref<any[]>([])
const result = ref('')
async function createBackup() { result.value = JSON.stringify(await jsonFetch(`${connectorsUrl}/api/connectors/backup/export`, { method: 'POST', body: JSON.stringify({ include_runtime: false }) }), null, 2); await load() }
async function upload(provider: 'google'|'microsoft') { result.value = JSON.stringify(await jsonFetch(`${connectorsUrl}/api/connectors/backup/export-upload`, { method: 'POST', body: JSON.stringify({ provider, include_runtime: false }) }), null, 2); await load() }
async function load() { backups.value = await jsonFetch<any[]>(`${connectorsUrl}/api/connectors/backup/manifests`) }
load()
</script>
