<template>
  <q-page class="column q-gutter-lg">
    <section class="hero-panel">
      <div class="eyebrow">Phase 12 Release</div>
      <h1>Release Center</h1>
      <p>Build, sign, verify, and archive Android, desktop, and web release artifacts.</p>
      <div class="row q-gutter-sm">
        <q-btn color="primary" icon="mdi-cloud-upload-outline" label="Export backup" @click="backup(false)" />
        <q-btn color="secondary" icon="mdi-google-drive" label="Upload Google backup" @click="backup(true, 'google')" />
        <q-btn color="secondary" icon="mdi-microsoft-onedrive" label="Upload OneDrive backup" @click="backup(true, 'microsoft')" />
      </div>
    </section>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-4" v-for="artifact in artifacts" :key="artifact.id">
        <q-card class="glass-card full-height">
          <q-card-section>
            <q-icon :name="artifact.icon" size="32px" />
            <div class="text-h6 q-mt-sm">{{ artifact.title }}</div>
            <p>{{ artifact.description }}</p>
            <q-list dense bordered separator>
              <q-item v-for="cmd in artifact.commands" :key="cmd"><q-item-section><code>{{ cmd }}</code></q-item-section></q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-card class="glass-card" v-if="lastResult">
      <q-card-section>
        <div class="text-h6">Last operation</div>
        <pre class="code-block">{{ JSON.stringify(lastResult, null, 2) }}</pre>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { connectorsUrl, jsonFetch } from '../services/api'
const lastResult = ref<any>(null)
const artifacts = [
  { id: 'web', icon: 'mdi-web', title: 'Web', description: 'Static SPA bundle for browser and Capacitor.', commands: ['pnpm --dir apps/web build'] },
  { id: 'android', icon: 'mdi-android', title: 'Android', description: 'Signed APK/AAB when keystore secrets are present.', commands: ['./scripts/release/build-android-signed.sh'] },
  { id: 'desktop', icon: 'mdi-desktop-classic', title: 'Desktop', description: 'Tauri bundle with optional updater/signing metadata.', commands: ['./scripts/release/build-tauri-signed.sh'] },
]
async function backup(upload: boolean, provider?: string) {
  const endpoint = upload ? `${connectorsUrl}/api/connectors/backup/export-upload` : `${connectorsUrl}/api/connectors/backup/export`
  lastResult.value = await jsonFetch(endpoint, { method: 'POST', body: JSON.stringify(upload ? { provider, include_runtime: false } : { include_runtime: false }) })
}
</script>
