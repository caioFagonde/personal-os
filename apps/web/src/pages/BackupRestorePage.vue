<template>
  <q-page class="column q-gutter-lg">
    <section class="hero-panel">
      <div class="eyebrow">Continuity</div>
      <h1>Backup & Restore</h1>
      <p>Create local backups and upload encrypted bundles to Google Drive or OneDrive once OAuth is connected.</p>
    </section>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <div class="row q-gutter-sm">
      <q-btn color="primary" icon="mdi-archive-arrow-up" label="Create local backup" :loading="creating" @click="createBackup" />
      <q-btn color="secondary" icon="mdi-google-drive" label="Upload to Google Drive" @click="upload('google')" />
      <q-btn color="secondary" icon="mdi-microsoft-onedrive" label="Upload to OneDrive" @click="upload('microsoft')" />
      <q-btn outline color="primary" icon="mdi-refresh" label="List backups" :loading="loading" @click="load" />
    </div>

    <q-card v-if="backups.length" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Backups</div>
        <q-list bordered separator class="rounded-borders">
          <q-item v-for="b in backups" :key="b.backup_id">
            <q-item-section>
              <q-item-label>{{ b.backup_id }}</q-item-label>
              <q-item-label caption>{{ b.archive_path }}</q-item-label>
              <q-item-label v-if="b.remote_uri" caption>Remote: {{ b.remote_uri }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <q-card v-if="result" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Result</div>
        <pre class="code-block">{{ result }}</pre>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { connectorsUrl, jsonFetch } from '../services/api'

const backups = ref<any[]>([])
const result = ref('')
const error = ref('')
const loading = ref(false)
const creating = ref(false)

async function createBackup() {
  creating.value = true
  error.value = ''
  try {
    const res = await jsonFetch(`${connectorsUrl}/api/connectors/backup/export`, {
      method: 'POST',
      body: JSON.stringify({ include_runtime: false }),
    })
    result.value = JSON.stringify(res, null, 2)
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    creating.value = false
  }
}

async function upload(provider: 'google' | 'microsoft') {
  error.value = ''
  try {
    const res = await jsonFetch(`${connectorsUrl}/api/connectors/backup/export-upload`, {
      method: 'POST',
      body: JSON.stringify({ provider, include_runtime: false }),
    })
    result.value = JSON.stringify(res, null, 2)
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function load() {
  loading.value = true
  try {
    backups.value = await jsonFetch<any[]>(`${connectorsUrl}/api/connectors/backup/manifests`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
