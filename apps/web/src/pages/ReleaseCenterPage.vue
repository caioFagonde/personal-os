<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Release" title="Release Center" subtitle="Build, sign, verify, and archive Android, desktop, and web release artifacts.">
      <template #actions>
        <q-btn color="primary" icon="mdi-cloud-upload-outline" label="Export backup" :loading="loading" @click="backup(false)" />
        <q-btn color="secondary" icon="mdi-google-drive" label="Upload Google backup" @click="backup(true, 'google')" />
        <q-btn color="secondary" icon="mdi-microsoft-onedrive" label="Upload OneDrive backup" @click="backup(true, 'microsoft')" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <div class="module-grid">
      <q-card v-for="artifact in artifacts" :key="artifact.id" class="glass-card">
        <q-card-section>
          <div class="row items-center q-gutter-sm q-mb-sm">
            <q-icon :name="artifact.icon" size="28px" />
            <div class="text-h6">{{ artifact.title }}</div>
          </div>
          <p style="color:var(--nexus-muted);font-size:13px">{{ artifact.description }}</p>
          <q-list dense bordered separator class="rounded-borders">
            <q-item v-for="cmd in artifact.commands" :key="cmd">
              <q-item-section><code>{{ cmd }}</code></q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
    </div>

    <q-card v-if="lastResult" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Last operation</div>
        <pre class="code-block">{{ JSON.stringify(lastResult, null, 2) }}</pre>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { connectorsUrl, jsonFetch } from '../services/api'

const lastResult = ref<any>(null)
const error = ref('')
const loading = ref(false)

const artifacts = [
  { id: 'web', icon: 'mdi-web', title: 'Web', description: 'Static SPA bundle for browser and Capacitor.', commands: ['pnpm --dir apps/web build'] },
  { id: 'android', icon: 'mdi-android', title: 'Android', description: 'Signed APK/AAB when keystore secrets are present.', commands: ['./scripts/release/build-android-signed.sh'] },
  { id: 'desktop', icon: 'mdi-desktop-classic', title: 'Desktop', description: 'Tauri bundle with optional updater/signing metadata.', commands: ['./scripts/release/build-tauri-signed.sh'] },
]

async function backup(upload: boolean, provider?: string) {
  loading.value = true
  error.value = ''
  try {
    const endpoint = upload ? `${connectorsUrl}/api/connectors/backup/export-upload` : `${connectorsUrl}/api/connectors/backup/export`
    lastResult.value = await jsonFetch(endpoint, {
      method: 'POST',
      body: JSON.stringify(upload ? { provider, include_runtime: false } : { include_runtime: false }),
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}
</script>
