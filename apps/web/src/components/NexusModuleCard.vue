<template>
  <q-card class="glass-card module-card-item">
    <q-card-section>
      <div class="row items-center no-wrap q-gutter-sm q-mb-sm">
        <q-avatar rounded color="primary" text-color="dark" :icon="icon" />
        <div>
          <div class="text-h6 q-mb-none" style="line-height:1.2">{{ title }}</div>
          <div class="text-caption" style="color:var(--nexus-muted)">{{ caption }}</div>
        </div>
        <q-space />
        <q-badge v-if="count !== undefined" color="primary" :label="count" />
        <q-badge v-else-if="badge" color="info" :label="badge" />
      </div>
      <p style="color:var(--nexus-muted);margin:0;font-size:13px;line-height:1.5">{{ body }}</p>
    </q-card-section>
    <q-card-actions align="between" style="padding-top:0">
      <q-btn flat color="primary" size="sm" :to="secondaryPath" :label="secondaryLabel" v-if="secondaryPath" />
      <q-space v-else />
      <q-btn flat color="primary" :to="path" :label="primaryLabel" icon-right="mdi-arrow-right" size="sm" />
    </q-card-actions>
  </q-card>
</template>
<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  caption?: string
  body?: string
  path: string
  icon?: string
  count?: number
  badge?: string
  primaryLabel?: string
  secondaryPath?: string
  secondaryLabel?: string
}>(), { primaryLabel: 'Open' })
</script>
<style scoped>
.module-card-item {
  min-height: 160px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
</style>
