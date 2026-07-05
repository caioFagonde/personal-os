<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Ops" title="Continuity" subtitle="Backups, sync, conflicts, offline queue, and device pairing — one surface, four health tiles.">
      <template #actions>
        <q-btn outline icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
      </template>
    </NexusPageHero>

    <!-- The four health tiles (BACKUP_RESTORE_SPEC / UX spec surface 12) -->
    <div class="row q-col-gutter-md">
      <div class="col-6 col-md-3">
        <MetricCard label="Last backup" :value="backupAge" icon="mdi-cloud-upload-outline" />
      </div>
      <div class="col-6 col-md-3">
        <MetricCard label="Sync" :value="syncStatus" icon="mdi-sync-circle" />
      </div>
      <div class="col-6 col-md-3">
        <MetricCard label="Conflicts" :value="conflictCount ?? '—'" icon="mdi-source-branch" />
      </div>
      <div class="col-6 col-md-3">
        <MetricCard label="Offline queue" :value="queueCount" icon="mdi-tray-full" />
      </div>
    </div>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-card class="glass-card">
      <q-tabs v-model="tab" dense align="left" no-caps active-color="primary" indicator-color="primary">
        <q-tab name="backup" label="Backup & Restore" />
        <q-tab name="sync" label="Sync Health" />
        <q-tab name="conflicts" label="Conflicts" />
        <q-tab name="queue" label="Offline Queue" />
        <q-tab name="pairing" label="Device Pairing" />
        <q-tab name="vault" label="Vault" />
      </q-tabs>
      <q-separator dark />
      <q-tab-panels v-model="tab" animated class="bg-transparent">
        <q-tab-panel name="backup"><BackupRestorePage /></q-tab-panel>
        <q-tab-panel name="sync"><SyncHealthPage /></q-tab-panel>
        <q-tab-panel name="conflicts"><ConflictResolutionPage /></q-tab-panel>
        <q-tab-panel name="queue"><OfflineQueuePage /></q-tab-panel>
        <q-tab-panel name="pairing"><DevicePairingPage /></q-tab-panel>
        <q-tab-panel name="vault" data-testid="vault-tab">
          <div v-if="vaultStatus" class="q-mb-md">
            <div class="row q-gutter-sm items-center">
              <q-badge :color="vaultStatus.write_enabled ? 'positive' : 'warning'" :label="vaultStatus.write_enabled ? 'write enabled' : 'dry-run'" />
              <span class="text-caption" style="color:var(--nexus-muted)">
                <span v-if="vaultStatus.last_run">last {{ vaultStatus.last_run.last_phase }}: {{ vaultStatus.last_run.at }}</span>
                <span v-else>indexer has not run yet</span>
              </span>
            </div>
          </div>
          <div v-else class="text-caption q-mb-md" style="color:var(--nexus-muted)">
            Vault not configured — set OBSIDIAN_VAULT_PATH and restart connector-service.
          </div>
          <q-list separator v-if="vaultConflicts.length">
            <q-item v-for="file in vaultConflicts" :key="file.relative_path">
              <q-item-section avatar><q-icon name="mdi-file-alert-outline" color="negative" /></q-item-section>
              <q-item-section>
                <q-item-label>{{ file.relative_path }}</q-item-label>
                <q-item-label caption>{{ file.detail || 'conflicting edits' }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="row q-gutter-xs">
                  <q-btn flat size="sm" color="primary" label="Keep app" @click="resolveVault(file.relative_path, 'keep_app')" />
                  <q-btn flat size="sm" color="primary" label="Keep vault" @click="resolveVault(file.relative_path, 'keep_vault')" />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
          <div v-else class="text-center q-py-md" style="color:var(--nexus-muted)">
            No vault conflicts. Sync runs from Settings → Obsidian vault.
          </div>
        </q-tab-panel>
      </q-tab-panels>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MetricCard from '../components/MetricCard.vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import BackupRestorePage from './BackupRestorePage.vue'
import SyncHealthPage from './SyncHealthPage.vue'
import ConflictResolutionPage from './ConflictResolutionPage.vue'
import OfflineQueuePage from './OfflineQueuePage.vue'
import DevicePairingPage from './DevicePairingPage.vue'
import { connectorsUrl, jsonFetch, syncUrl } from '../services/api'
import { loadQueue, pendingCount } from '../services/sync-queue'

const route = useRoute()
const router = useRouter()
const VALID_TABS = ['backup', 'sync', 'conflicts', 'queue', 'pairing', 'vault']
const initial = typeof route.query.tab === 'string' && VALID_TABS.includes(route.query.tab) ? route.query.tab : 'backup'
const tab = ref(initial)
watch(tab, (value) => { void router.replace({ query: { ...route.query, tab: value } }) })

const loading = ref(false)
const error = ref('')
const manifests = ref<{ created_at?: string }[]>([])
const syncHealth = ref<{ status?: string } | null>(null)
const conflictCount = ref<number | null>(null)

const queueCount = ref(0)

const backupAge = computed(() => {
  const iso = manifests.value[0]?.created_at
  if (!iso) return 'none'
  const hours = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
  return hours < 1 ? '<1h ✓' : hours < 48 ? `${hours}h` : `${Math.floor(hours / 24)}d`
})

const syncStatus = computed(() => (syncHealth.value ? (syncHealth.value.status || 'ok').toUpperCase() : '—'))

// Vault sync state (Phase D)
interface VaultStatus {
  write_enabled: boolean
  conflicts: number
  last_run: { last_phase: string; at: string } | null
}
interface VaultFile { relative_path: string; detail: string; status: string }

const vaultStatus = ref<VaultStatus | null>(null)
const vaultConflicts = ref<VaultFile[]>([])

async function resolveVault(path: string, resolution: 'keep_app' | 'keep_vault') {
  try {
    await jsonFetch(`${connectorsUrl}/api/connectors/obsidian/sync/resolve`, {
      method: 'POST',
      body: JSON.stringify({ relative_path: path, resolution, execute: true }),
    })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function load() {
  loading.value = true
  error.value = ''
  queueCount.value = pendingCount(await loadQueue())
  const results = await Promise.allSettled([
    jsonFetch<{ created_at?: string }[]>(`${connectorsUrl}/api/connectors/backup/manifests`),
    jsonFetch<{ status?: string }>(`${syncUrl}/api/sync/health`),
    jsonFetch<unknown[]>(`${syncUrl}/api/sync/conflicts`),
    jsonFetch<VaultStatus>(`${connectorsUrl}/api/connectors/obsidian/sync/status`),
    jsonFetch<VaultFile[]>(`${connectorsUrl}/api/connectors/obsidian/sync/files?status=conflict`),
  ])
  if (results[0].status === 'fulfilled') manifests.value = results[0].value
  if (results[1].status === 'fulfilled') syncHealth.value = results[1].value
  if (results[2].status === 'fulfilled') conflictCount.value = results[2].value.length
  vaultStatus.value = results[3].status === 'fulfilled' ? results[3].value : null
  vaultConflicts.value = results[4].status === 'fulfilled' ? results[4].value : []
  if (results.slice(0, 3).every((r) => r.status === 'rejected')) {
    error.value = 'Continuity endpoints unreachable — run make up.'
  }
  loading.value = false
}

onMounted(load)
</script>
<style scoped lang="scss">
// Embedded surfaces are full pages; inside a tab panel their layout-derived
// min-height must not force viewport-height panels.
:deep(.q-tab-panel .q-page) { min-height: auto !important; padding: 0; }
</style>
