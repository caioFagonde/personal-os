<template>
  <div class="nexus-empty text-center q-py-xl">
    <q-icon :name="icon" size="52px" style="opacity:.3" />
    <div class="text-subtitle1 q-mt-sm">{{ message }}</div>
    <div v-if="hint" class="text-caption q-mt-xs" style="color:var(--nexus-muted)">{{ hint }}</div>
  </div>
</template>
<script setup lang="ts">
withDefaults(defineProps<{
  icon?: string
  message: string
  hint?: string
}>(), { icon: 'mdi-inbox-outline' })
</script>
<style scoped>
.nexus-empty { color: var(--nexus-muted); }
</style>
