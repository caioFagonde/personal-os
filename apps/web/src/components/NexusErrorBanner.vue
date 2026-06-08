<template>
  <q-banner v-if="error" class="bg-negative text-white" rounded>
    <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
    {{ error }}
    <template #action>
      <q-btn flat color="white" label="Dismiss" @click="$emit('dismiss')" />
    </template>
  </q-banner>
</template>
<script setup lang="ts">
defineProps<{ error: string }>()
defineEmits<{ dismiss: [] }>()
</script>
