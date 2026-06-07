<template>
  <nav class="module-dock" aria-label="Primary modules">
    <div v-for="(group, name) in grouped" :key="name" class="module-dock__group">
      <div class="module-dock__heading">{{ name }}</div>
      <q-list dense>
        <q-item v-for="item in group" :key="item.id" clickable :to="item.path" exact class="module-dock__item">
          <q-item-section avatar><q-icon :name="item.icon" /></q-item-section>
          <q-item-section>{{ item.label }}</q-item-section>
        </q-item>
      </q-list>
    </div>
    <q-expansion-item icon="mdi-dots-horizontal" label="More" header-class="module-dock__heading" dense>
      <q-list dense>
        <q-item v-for="item in secondary" :key="item.id" clickable :to="item.path" exact class="module-dock__item">
          <q-item-section avatar><q-icon :name="item.icon" /></q-item-section>
          <q-item-section>{{ item.label }}</q-item-section>
        </q-item>
      </q-list>
    </q-expansion-item>
  </nav>
</template>
<script setup lang="ts">
import { groupNavigation, secondaryModules } from '../design/tokens'
const grouped = groupNavigation()
const secondary = secondaryModules
</script>
