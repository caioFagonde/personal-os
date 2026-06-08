<template>
  <div class="nexus-loading text-center q-py-xl">
    <q-spinner-orbit :size="size" color="primary" />
    <div v-if="message" class="text-subtitle2 q-mt-md" style="color:var(--nexus-muted)">{{ message }}</div>
  </div>
</template>
<script setup lang="ts">
withDefaults(defineProps<{
  message?: string
  size?: string
}>(), { size: '48px' })
</script>
