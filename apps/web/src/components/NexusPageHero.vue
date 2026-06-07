<template>
  <section class="hero-panel">
    <div class="eyebrow">{{ eyebrow }}</div>
    <h1>{{ title }}</h1>
    <p v-if="subtitle">{{ subtitle }}</p>
    <div v-if="$slots.actions" class="row q-gutter-sm q-mt-md">
      <slot name="actions" />
    </div>
  </section>
</template>
<script setup lang="ts">
defineProps<{ eyebrow: string; title: string; subtitle?: string }>()
</script>
