<template>
  <div class="status-ribbon glass-panel">
    <div class="status-ribbon__left">
      <q-icon :name="tone.icon" :color="tone.color" size="20px" />
      <div>
        <div class="status-ribbon__title">{{ tone.label }}</div>
        <div class="status-ribbon__caption">{{ caption }}</div>
      </div>
    </div>
    <div class="status-ribbon__metrics">
      <span>{{ onlineLabel }}</span>
      <span>{{ pendingMutations }} pending</span>
      <span>{{ conflicts }} conflicts</span>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { normalizeStatus, statusTone } from '../design/tokens'
const props = defineProps<{ status?: string; pendingMutations?: number; conflicts?: number; online?: boolean }>()
const statusKey = computed(() => normalizeStatus(props.status))
const tone = computed(() => statusTone[statusKey.value])
const pendingMutations = computed(() => props.pendingMutations ?? 0)
const conflicts = computed(() => props.conflicts ?? 0)
const onlineLabel = computed(() => props.online === false ? 'offline' : 'online')
const caption = computed(() => conflicts.value > 0 ? 'Manual resolution required' : 'Local-first substrate ready')
</script>
