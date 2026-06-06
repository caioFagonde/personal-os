<template>
  <q-card class="metric-card glass-panel" flat>
    <q-card-section>
      <div class="row items-center no-wrap">
        <q-icon :name="icon" size="28px" class="q-mr-md" />
        <div>
          <div class="metric-card__label">{{ label }}</div>
          <div class="metric-card__value">{{ value }}</div>
        </div>
      </div>
    </q-card-section>
  </q-card>
</template>
<script setup lang="ts">
defineProps<{ label: string; value: string | number; icon: string }>()
</script>
