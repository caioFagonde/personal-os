<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Continuity" title="Backup & Restore" subtitle="Create encrypted local backups, then upload them only to providers you explicitly configure." />
    <q-banner v-if="error" class="bg-negative text-white" rounded>{{ error }}</q-banner>
    <q-banner v-if="status && !status.encryption.configured" class="bg-warning text-dark" rounded>
      Backup export is blocked until <code>BACKUP_ENCRYPTION_KEY</code> is configured. Plaintext export is disabled.
    </q-banner>

    <!-- Phase E5: the four continuity health tiles (all live). -->
    <div v-if="continuity" class="row q-col-gutter-md" data-testid="backup-tiles">
      <div class="col-6 col-md-3"><MetricCard label="Last backup" :value="lastBackupTile" icon="mdi-archive-clock-outline" /></div>
      <div class="col-6 col-md-3"><MetricCard label="Remote copy" :value="remoteTile" icon="mdi-cloud-check-outline" /></div>
      <div class="col-6 col-md-3"><MetricCard label="Restore drill" :value="drillTile" icon="mdi-history" /></div>
      <div class="col-6 col-md-3"><MetricCard label="Snapshots" :value="retentionTile" icon="mdi-database-outline" /></div>
    </div>

    <!-- Ops runner buttons: approval-gated command-bus templates, never raw shell. -->
    <div class="row q-gutter-sm" data-testid="backup-ops">
      <q-btn color="primary" icon="mdi-archive-arrow-down-outline" label="Back up now" :loading="opsBusy" @click="runOp('backup.create')" />
      <q-btn outline color="primary" icon="mdi-check-decagram-outline" label="Verify latest" :loading="opsBusy" @click="runOp('backup.verify')" />
      <q-btn outline color="primary" icon="mdi-restore" label="Run drill" :loading="opsBusy" @click="runOp('backup.drill')" />
      <q-btn outline icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
    </div>
    <q-banner v-if="opsMessage" class="bg-info text-dark" rounded>{{ opsMessage }}</q-banner>

    <q-expansion-item icon="mdi-cog-outline" label="Direct export (advanced)" class="glass-card">
      <div class="row q-gutter-sm q-pa-md">
        <q-btn color="primary" icon="mdi-archive-lock" label="Create encrypted backup" :loading="creating" :disable="status && !status.encryption.configured" @click="createBackup" />
        <q-btn color="secondary" icon="mdi-google-drive" label="Upload to Google Drive" :disable="status && !status.encryption.configured" @click="upload('google')" />
        <q-btn color="secondary" icon="mdi-microsoft-onedrive" label="Upload to OneDrive" :disable="status && !status.encryption.configured" @click="upload('microsoft')" />
      </div>
    </q-expansion-item>

    <div v-if="status" class="module-grid">
      <q-card v-for="provider in providerCards" :key="provider.id" class="glass-card">
        <q-card-section>
          <div class="row items-center justify-between"><div class="text-h6">{{ provider.title }}</div><q-badge :color="provider.configured ? 'positive' : 'warning'">{{ provider.status }}</q-badge></div>
          <p>{{ provider.credential_policy }}</p>
          <div class="text-caption">Required setup: {{ provider.required_env.join(', ') }}</div>
          <div class="text-caption q-mt-sm">Manual setup only. Personal OS never provisions paid cloud resources.</div>
        </q-card-section>
      </q-card>
    </div>
    <q-card v-if="backups.length" class="glass-card"><q-card-section><div class="text-h6 q-mb-sm">Encrypted backups</div><q-list bordered separator><q-item v-for="b in backups" :key="b.backup_id"><q-item-section><q-item-label>{{ b.backup_id }}</q-item-label><q-item-label caption>{{ b.archive_path }}<span v-if="b.verified_at"> · verified ✓</span></q-item-label></q-item-section></q-item></q-list></q-card-section></q-card>
    <q-card v-if="result" class="glass-card"><q-card-section><pre class="code-block">{{ result }}</pre></q-card-section></q-card>
  </q-page>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import MetricCard from '../components/MetricCard.vue'
import { commandUrl, connectorsUrl, deviceKey, jsonFetch } from '../services/api'
const backups = ref<any[]>([]); const status = ref<any>(null); const result = ref(''); const error = ref(''); const loading = ref(false); const creating = ref(false)
const continuity = ref<any>(null); const opsBusy = ref(false); const opsMessage = ref('')
const providerCards = computed(() => status.value ? [{ title: 'Azure Blob', ...status.value.providers.azure_blob }, { title: 'AWS S3', ...status.value.providers.aws_s3 }] : [])

function ageLabel(iso?: string): string {
  if (!iso) return 'none'
  const h = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
  return h < 1 ? '<1h' : h < 48 ? `${h}h` : `${Math.floor(h / 24)}d`
}
const lastBackupTile = computed(() => {
  const l = continuity.value?.latest
  if (!l) return 'none'
  return `${ageLabel(l.created_at)}${l.verified_at ? ' ✓' : ''}`
})
const remoteTile = computed(() => (continuity.value?.remote ? ageLabel(continuity.value.remote.completed_at) : 'none'))
const drillTile = computed(() => {
  const d = continuity.value?.last_drill
  if (!d) return 'never'
  return `${d.status} ${ageLabel(d.completed_at || d.started_at)}`
})
const retentionTile = computed(() => {
  const r = continuity.value?.retention
  return r ? `${r.verified_snapshots}/${r.total_snapshots} verified` : '—'
})

// The three buttons create approval-gated command requests against the
// backup.* templates (seeded in migration 017). The trusted host runner
// executes them after approval — the UI never runs shell itself.
async function runOp(templateId: string) {
  opsBusy.value = true; opsMessage.value = ''; error.value = ''
  try {
    const res = await jsonFetch<{ id: string; status: string }>(`${commandUrl}/api/commands`, {
      method: 'POST',
      body: JSON.stringify({ requester_device_key: deviceKey(), target_device_key: 'host-runner', template_id: templateId, scopes: ['backup.write'] }),
    })
    opsMessage.value = `Requested "${templateId}" — status: ${res.status}. Approve it from the approvals queue; it never runs shell from the browser.`
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    opsBusy.value = false
  }
}

async function createBackup() { creating.value = true; error.value = ''; try { const res = await jsonFetch(`${connectorsUrl}/api/connectors/backup/export`, { method: 'POST', body: JSON.stringify({ include_runtime: false }) }); result.value = JSON.stringify(res, null, 2); await load() } catch (err) { error.value = err instanceof Error ? err.message : String(err) } finally { creating.value = false } }
async function upload(provider: 'google' | 'microsoft') { creating.value = true; error.value = ''; try { const res = await jsonFetch(`${connectorsUrl}/api/connectors/backup/export-upload`, { method: 'POST', body: JSON.stringify({ provider, include_runtime: false }) }); result.value = JSON.stringify(res, null, 2); await load() } catch (err) { error.value = err instanceof Error ? err.message : String(err) } finally { creating.value = false } }
async function load() {
  loading.value = true; error.value = ''
  try {
    const [s, b, c] = await Promise.all([
      jsonFetch(`${connectorsUrl}/api/connectors/backup/status`),
      jsonFetch<any[]>(`${connectorsUrl}/api/connectors/backup/manifests`),
      jsonFetch(`${connectorsUrl}/api/connectors/backup/continuity`).catch(() => null),
    ])
    status.value = s; backups.value = b; continuity.value = c
  } catch (err) { error.value = err instanceof Error ? err.message : String(err) } finally { loading.value = false }
}
onMounted(load)
</script>
