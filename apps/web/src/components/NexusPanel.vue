<template>
  <section :class="['nexus-panel', { 'nexus-panel--flat': flat }]">
    <div v-if="title" class="nexus-panel__header">
      <div>
        <div class="nexus-panel__title">{{ title }}</div>
        <div v-if="subtitle" class="nexus-panel__subtitle">{{ subtitle }}</div>
      </div>
      <slot name="header-actions" />
    </div>
    <slot />
  </section>
</template>
<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  subtitle?: string
  flat?: boolean
}>(), { flat: false })
</script>
<style scoped>
.nexus-panel {
  background: linear-gradient(180deg, rgba(21, 31, 55, 0.94), rgba(11, 18, 34, 0.92));
  border: 1px solid var(--nexus-border);
  border-radius: 22px;
  padding: clamp(16px, 2.5vw, 28px);
}
.nexus-panel--flat {
  background: transparent;
  border: none;
  padding: 0;
}
.nexus-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.nexus-panel__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--nexus-text);
}
.nexus-panel__subtitle {
  font-size: 13px;
  color: var(--nexus-muted);
  margin-top: 2px;
}
</style>
