<script setup>
// The shared body of the in-shell status pages (permission denied, not
// found): one panel, an HTTP eyebrow, a status badge, and a way home.
import GmPanel from "../components/GmPanel.vue";
import GmStatusBadge from "../components/GmStatusBadge.vue";

defineProps({
  eyebrow: { type: String, required: true },
  title: { type: String, required: true },
  badgeStatus: { type: String, default: "neutral" },
  badgeLabel: { type: String, required: true },
});
</script>

<template>
  <GmPanel class="gm-status-page" :title="title">
    <p class="gm-status-page__eyebrow gm-mono">{{ eyebrow }}</p>
    <GmStatusBadge :status="badgeStatus" :label="badgeLabel" />
    <div class="gm-status-page__body"><slot /></div>
    <div class="gm-status-page__actions"><slot name="actions" /></div>
  </GmPanel>
</template>

<style scoped>
.gm-status-page {
  max-width: 560px;
}

.gm-status-page__eyebrow {
  margin-bottom: var(--sp-3);
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
  color: var(--paper-500);
}

.gm-status-page__body {
  margin-top: var(--sp-4);
  color: var(--paper-300);
}

.gm-status-page__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin-top: var(--sp-5);
}
</style>
