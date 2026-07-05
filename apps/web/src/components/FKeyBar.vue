<template>
  <nav class="fkey-bar" aria-label="Function keys">
    <span
      v-for="seg in segments"
      :key="seg.key"
      class="fkey-bar__seg"
      :class="{ 'seg--warn': seg.tone === 'warn', 'seg--alarm': seg.tone === 'alarm' }"
      role="button"
      tabindex="0"
      :data-testid="`fkey-${seg.key.toLowerCase()}`"
      @click="go(seg.path)"
      @keyup.enter="go(seg.path)"
    ><b>{{ seg.key }}</b>{{ seg.label }}</span>
    <span class="fkey-bar__clock">{{ clock }}</span>
  </nav>
</template>
<script setup lang="ts">
// GREEN GLASS function-key bar (DESIGN_LANGUAGE.md R2.3). Every segment is a
// live readout — no hardcoded metric values — and its F-key actually works.
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { codingAgentUrl, connectorsUrl, jsonFetch, syncUrl } from '../services/api'
import { loadQueue, pendingCount } from '../services/sync-queue'

type Tone = 'ok' | 'warn' | 'alarm'
interface Segment { key: string; label: string; path: string; tone: Tone }

const router = useRouter()
const clock = ref('')

const syncState = ref<string>('…')
const syncTone = ref<Tone>('warn')
const queueCount = ref<number | null>(null)
const backupAge = ref<string>('…')
const backupTone = ref<Tone>('warn')
const agentCount = ref<number | null>(null)
const agentTone = ref<Tone>('ok')
const conflictCount = ref<number | null>(null)

const segments = computed<Segment[]>(() => [
  { key: 'F2', label: 'CAPTURE', path: '/capture', tone: 'ok' },
  { key: 'F4', label: agentCount.value === null ? 'AGENTS ?' : `AGENTS·${agentCount.value}`, path: '/coding-agent', tone: agentTone.value },
  { key: 'F5', label: `SYNC ${syncState.value}`, path: '/sync-health', tone: syncTone.value },
  { key: 'F6', label: queueCount.value === null ? 'QUEUE ?' : `QUEUE·${queueCount.value}`, path: '/offline-queue', tone: queueCount.value ? 'warn' : 'ok' },
  { key: 'F7', label: conflictCount.value === null ? 'CONFLICT ?' : `CONFLICT·${conflictCount.value}`, path: '/conflicts', tone: conflictCount.value ? 'alarm' : 'ok' },
  { key: 'F9', label: `BACKUP ${backupAge.value}`, path: '/backup-restore', tone: backupTone.value },
])

const F_KEY_PATHS: Record<string, string> = {
  F2: '/capture',
  F4: '/coding-agent',
  F5: '/sync-health',
  F6: '/offline-queue',
  F7: '/conflicts',
  F9: '/backup-restore',
}

function go(path: string) { void router.push(path) }

function onKeydown(event: KeyboardEvent) {
  const path = F_KEY_PATHS[event.key]
  if (path) {
    event.preventDefault()
    go(path)
  }
}

function ageLabel(iso: string | undefined): string {
  if (!iso) return 'NONE'
  const hours = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
  if (hours < 1) return '<1h ✓'
  if (hours < 48) return `${hours}h${hours <= 24 ? ' ✓' : ''}`
  return `${Math.floor(hours / 24)}d`
}

async function refresh() {
  queueCount.value = pendingCount(await loadQueue())
  try {
    const health = await jsonFetch<{ status?: string; pending?: number }>(`${syncUrl}/api/sync/health`)
    syncState.value = (health.status || 'ok').toUpperCase()
    syncTone.value = health.status === 'ok' ? 'ok' : 'warn'
  } catch { syncState.value = 'DOWN'; syncTone.value = 'alarm' }
  try {
    const conflicts = await jsonFetch<unknown[]>(`${syncUrl}/api/sync/conflicts`)
    conflictCount.value = conflicts.length
  } catch { conflictCount.value = null }
  try {
    const manifests = await jsonFetch<{ created_at?: string }[]>(`${connectorsUrl}/api/connectors/backup/manifests`)
    backupAge.value = ageLabel(manifests[0]?.created_at)
    backupTone.value = manifests.length && backupAge.value.includes('✓') ? 'ok' : 'warn'
  } catch { backupAge.value = '?'; backupTone.value = 'warn' }
  try {
    const jobs = await jsonFetch<{ status: string }[]>(`${codingAgentUrl}/api/coding-agent/jobs`)
    const active = jobs.filter((j) => ['running', 'queued', 'pending_approval'].includes(j.status))
    agentCount.value = active.length
    agentTone.value = active.some((j) => j.status === 'pending_approval') ? 'warn' : 'ok'
  } catch { agentCount.value = null }
}

let timer: ReturnType<typeof setInterval> | undefined
let clockTimer: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  const tick = () => { clock.value = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
  tick()
  clockTimer = setInterval(tick, 30_000)
  void refresh()
  timer = setInterval(() => { void refresh() }, 60_000)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  if (timer) clearInterval(timer)
  if (clockTimer) clearInterval(clockTimer)
})
</script>
<style scoped lang="scss">
.fkey-bar__seg { cursor: pointer; white-space: nowrap; }
.fkey-bar__seg:focus-visible { outline: 2px solid var(--nexus-warn); outline-offset: 2px; }
.fkey-bar__clock { margin-left: auto; color: var(--nexus-muted); }
@media (max-width: 720px) {
  .fkey-bar { display: none; } // mobile is a handheld terminal — no chassis furniture
}
</style>
