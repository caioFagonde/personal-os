<template>
  <q-page class="q-pa-md q-gutter-md">
    <section class="hero-card glass-panel">
      <div class="text-overline">Phase 13</div>
      <h1>Live Stack Certification</h1>
      <p>Run browser tests against the actual Docker stack, certify mobile sync, and inspect release readiness.</p>
    </section>
    <div class="row q-col-gutter-md">
      <div v-for="item in items" :key="item.title" class="col-12 col-md-6">
        <q-card class="glass-panel" bordered>
          <q-card-section>
            <q-icon :name="item.icon" size="32px" />
            <div class="text-h6 q-mt-sm">{{ item.title }}</div>
            <p>{{ item.body }}</p>
            <code>{{ item.command }}</code>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>
<script setup lang="ts">
const items = [
  { icon: 'mdi-web', title: 'Live Playwright', body: 'Run UI flows against Docker services, not only static SPA.', command: 'make certify-live-stack' },
  { icon: 'mdi-cellphone-link', title: 'Physical Android sync', body: 'Deploy APK, adb reverse ports, create offline mutation, and verify sync health.', command: 'make certify-physical-sync' },
  { icon: 'mdi-brain', title: 'Model runtime', body: 'Certify OCR/object/audio runtime fallback and provider readiness.', command: 'make certify-model-runtime' },
  { icon: 'mdi-package-up', title: 'Publish release', body: 'Create signed artifacts and optionally publish a GitHub release.', command: 'make publish-release' }
]
</script>
