<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Continuity" title="Backup & Restore" subtitle="Create encrypted local backups, then upload them only to providers you explicitly configure." />
    <q-banner v-if="error" class="bg-negative text-white" rounded>{{ error }}</q-banner>
    <q-banner v-if="status && !status.encryption.configured" class="bg-warning text-dark" rounded>
      Backup export is blocked until <code>BACKUP_ENCRYPTION_KEY</code> is configured. Plaintext export is disabled.
    </q-banner>
    <div class="row q-gutter-sm">
      <q-btn color="primary" icon="mdi-archive-lock" label="Create encrypted backup" :loading="creating" :disable="status && !status.encryption.configured" @click="createBackup" />
      <q-btn color="secondary" icon="mdi-google-drive" label="Upload to Google Drive" :disable="status && !status.encryption.configured" @click="upload('google')" />
      <q-btn color="secondary" icon="mdi-microsoft-onedrive" label="Upload to OneDrive" :disable="status && !status.encryption.configured" @click="upload('microsoft')" />
      <q-btn outline color="primary" icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
    </div>
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
    <q-card v-if="backups.length" class="glass-card"><q-card-section><div class="text-h6 q-mb-sm">Encrypted backups</div><q-list bordered separator><q-item v-for="b in backups" :key="b.backup_id"><q-item-section><q-item-label>{{ b.backup_id }}</q-item-label><q-item-label caption>{{ b.archive_path }}</q-item-label></q-item-section></q-item></q-list></q-card-section></q-card>
    <q-card v-if="result" class="glass-card"><q-card-section><pre class="code-block">{{ result }}</pre></q-card-section></q-card>
  </q-page>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { connectorsUrl, jsonFetch } from '../services/api'
const backups = ref<any[]>([]); const status = ref<any>(null); const result = ref(''); const error = ref(''); const loading = ref(false); const creating = ref(false)
const providerCards = computed(() => status.value ? [{ title: 'Azure Blob', ...status.value.providers.azure_blob }, { title: 'AWS S3', ...status.value.providers.aws_s3 }] : [])
async function createBackup() { creating.value = true; error.value = ''; try { const res = await jsonFetch(`${connectorsUrl}/api/connectors/backup/export`, { method: 'POST', body: JSON.stringify({ include_runtime: false }) }); result.value = JSON.stringify(res, null, 2); await load() } catch (err) { error.value = err instanceof Error ? err.message : String(err) } finally { creating.value = false } }
async function upload(provider: 'google' | 'microsoft') { creating.value = true; error.value = ''; try { const res = await jsonFetch(`${connectorsUrl}/api/connectors/backup/export-upload`, { method: 'POST', body: JSON.stringify({ provider, include_runtime: false }) }); result.value = JSON.stringify(res, null, 2); await load() } catch (err) { error.value = err instanceof Error ? err.message : String(err) } finally { creating.value = false } }
async function load() { loading.value = true; error.value = ''; try { [status.value, backups.value] = await Promise.all([jsonFetch(`${connectorsUrl}/api/connectors/backup/status`), jsonFetch<any[]>(`${connectorsUrl}/api/connectors/backup/manifests`)]) } catch (err) { error.value = err instanceof Error ? err.message : String(err) } finally { loading.value = false } }
onMounted(load)
</script>
