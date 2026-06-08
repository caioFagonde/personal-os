<template>
  <q-badge :color="color" :label="label" />
</template>
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  map?: Record<string, string>
}>()

const defaultMap: Record<string, string> = {
  ok: 'positive',
  connected: 'positive',
  configured: 'positive',
  active: 'positive',
  completed: 'positive',
  succeeded: 'positive',
  healthy: 'positive',
  running: 'primary',
  pending: 'info',
  queued: 'info',
  'dry-run': 'info',
  dry_run: 'info',
  warning: 'warning',
  pending_approval: 'warning',
  degraded: 'warning',
  inactive: 'grey',
  offline: 'grey',
  unknown: 'grey',
  failed: 'negative',
  error: 'negative',
  down: 'negative',
}

const color = computed(() => {
  const merged = { ...defaultMap, ...(props.map || {}) }
  return merged[props.status] ?? 'grey'
})

const label = computed(() => props.status.replace(/_/g, ' '))
</script>
