<template>
  <div v-if="visible" class="bios-boot" data-testid="bios-boot" @click="skip">
    <pre class="bios-boot__screen">{{ rendered }}</pre>
    <div class="bios-boot__hint">PRESS ANY KEY TO SKIP</div>
  </div>
</template>
<script setup lang="ts">
// GREEN GLASS BIOS self-test (DESIGN_LANGUAGE.md R2.4).
// Plays once per session, any key skips, prefers-reduced-motion bypasses it
// entirely. Service states are HONEST: fetched live from the gateway
// (/api/control/health), never invented. While a probe is in flight the line
// reads "...."; unreachable renders as DOWN in alarm text, degraded as amber.
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { apiUrl, jsonFetch } from '../services/api'

const SESSION_KEY = 'nexus-bios-boot-shown'
const LINE_MS = 160
const HOLD_MS = 700

const visible = ref(false)
const lines = ref<string[]>([])
const shown = ref(0)
let timers: ReturnType<typeof setTimeout>[] = []

const rendered = computed(() => lines.value.slice(0, shown.value).join('\n'))

function pad(name: string): string {
  return `${name} `.padEnd(22, '.')
}

async function probe(): Promise<string[]> {
  const out = ['NEXUS/OS BIOS v1.0 — GREEN GLASS']
  // Real heap ceiling when the browser exposes it; no invented numbers.
  const heap = (performance as { memory?: { jsHeapSizeLimit: number } }).memory?.jsHeapSizeLimit
  if (heap) out.push(`MEMORY TEST ......... ${Math.round(heap / 1048576)} MB OK`)
  out.push('')
  try {
    const health = await jsonFetch<{ status: string; services: Record<string, { ok: boolean }> }>(
      `${apiUrl}/api/control/health`)
    for (const [name, state] of Object.entries(health.services)) {
      out.push(`${pad(name.toUpperCase())} ${state.ok ? 'OK' : 'DEGRADED'}`)
    }
    out.push('', `SYSTEM ${health.status === 'ok' ? 'READY.' : 'DEGRADED — CHECK /ops.'}`)
  } catch {
    try {
      const health = await jsonFetch<{ status: string; modules?: number }>(`${apiUrl}/health`)
      out.push(`${pad('API GATEWAY')} ${health.status === 'ok' ? 'OK' : 'DEGRADED'}`)
      out.push('', 'SYSTEM READY (PARTIAL SELF-TEST).')
    } catch {
      out.push(`${pad('API GATEWAY')} DOWN`)
      out.push('', 'STACK OFFLINE — run make up.')
    }
  }
  return out
}

function skip() {
  finish()
}

function onKeydown() {
  skip()
}

function finish() {
  visible.value = false
  timers.forEach(clearTimeout)
  timers = []
  window.removeEventListener('keydown', onKeydown)
}

onMounted(async () => {
  if (sessionStorage.getItem(SESSION_KEY)) return
  sessionStorage.setItem(SESSION_KEY, '1')
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reducedMotion) return
  visible.value = true
  window.addEventListener('keydown', onKeydown)
  lines.value = await probe()
  if (!visible.value) return // skipped while probing
  lines.value.forEach((_, i) => {
    timers.push(setTimeout(() => { shown.value = i + 1 }, i * LINE_MS))
  })
  timers.push(setTimeout(finish, lines.value.length * LINE_MS + HOLD_MS))
})

onUnmounted(finish)
</script>
<style scoped lang="scss">
.bios-boot {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: var(--nexus-bg, #0a140c);
  color: var(--nexus-text, #5dff86);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  padding: 6vh 8vw;
  cursor: pointer;
}
.bios-boot__screen {
  font-family: inherit;
  font-size: 19px;
  line-height: 1.35;
  margin: 0;
  white-space: pre-wrap;
}
.bios-boot__hint {
  margin-top: auto;
  color: var(--nexus-muted, #2f9a55);
  font-size: 16px;
  letter-spacing: 2px;
}
</style>
