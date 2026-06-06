<template>
  <q-page class="column q-gutter-lg">
    <section class="hero-panel">
      <div class="eyebrow">Phase 12 Certification</div>
      <h1>Device & Release Certification</h1>
      <p>Run browser, Android, connector, restore, and release checks before trusting a build for daily operation.</p>
      <div class="row q-gutter-sm">
        <q-btn color="primary" icon="mdi-refresh" label="Refresh status" @click="load" />
        <q-btn color="secondary" icon="mdi-clipboard-check-outline" label="Copy local test commands" @click="copyCommands" />
      </div>
    </section>

    <div class="row q-col-gutter-md">
      <div v-for="item in matrix" :key="item.id" class="col-12 col-md-6 col-lg-4">
        <q-card class="glass-card full-height">
          <q-card-section>
            <div class="row items-center justify-between">
              <div class="text-h6">{{ item.title }}</div>
              <q-badge :color="item.required ? 'primary' : 'grey'">{{ item.required ? 'required' : 'optional' }}</q-badge>
            </div>
            <p class="text-body2 q-mt-sm">{{ item.description }}</p>
            <q-list dense bordered separator class="rounded-borders">
              <q-item v-for="cmd in item.commands" :key="cmd">
                <q-item-section><code>{{ cmd }}</code></q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6">Connector readiness</div>
        <pre class="code-block">{{ JSON.stringify(status, null, 2) }}</pre>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { copyToClipboard, Notify } from 'quasar'
import { connectorsUrl, jsonFetch } from '../services/api'

const status = ref<any>({})
const matrix = [
  { id: 'web-e2e', title: 'Browser E2E', required: true, description: 'Validates premium shell routes on desktop and mobile viewports.', commands: ['pnpm install --frozen-lockfile=false', 'pnpm --dir apps/web build', 'pnpm exec playwright test'] },
  { id: 'android-emulator', title: 'Android emulator', required: true, description: 'Builds and launches the Capacitor app on a clean emulator.', commands: ['./scripts/certify/android-emulator.sh'] },
  { id: 'physical-android', title: 'Physical Android', required: false, description: 'Detects a USB device, waits for authorization, installs APK, and configures adb reverse.', commands: ['./scripts/certify/physical-android.sh'] },
  { id: 'restore-drill', title: 'Restore drill', required: true, description: 'Creates data, exports backup, destroys/restarts services, and verifies continuity.', commands: ['make restore-drill'] },
  { id: 'live-connectors', title: 'Live connectors', required: false, description: 'Runs optional sandbox sends/uploads only when secrets are present.', commands: ['./scripts/certify/live-connectors.sh'] },
  { id: 'release', title: 'Release signing', required: true, description: 'Builds signed Android and Tauri artifacts when signing secrets are available.', commands: ['./scripts/release/build-android-signed.sh', './scripts/release/build-tauri-signed.sh'] },
]
async function load() {
  try { status.value = await jsonFetch(`${connectorsUrl}/api/connectors/status`) } catch (e: any) { status.value = { error: e.message } }
}
async function copyCommands() {
  await copyToClipboard(matrix.flatMap((m) => m.commands).join('\n'))
  Notify.create({ type: 'positive', message: 'Certification commands copied' })
}
onMounted(load)
</script>
