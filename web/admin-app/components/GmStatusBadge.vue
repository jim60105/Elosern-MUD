<script setup>
// A status marker (gm-portal-s1-foundation): wraps the shared not-color-only
// `.status-marker` utility, so every state pairs color with a glyph, a
// border style (solid / dashed / double) and a text label.
import { computed } from "vue";

const props = defineProps({
  status: {
    type: String,
    default: "neutral",
    validator: (value) => ["ok", "warn", "crit", "neutral"].includes(value),
  },
  label: { type: String, required: true },
});

const classes = computed(() => [
  "status-marker",
  "gm-status-badge",
  props.status === "neutral" ? "gm-status-badge--neutral" : `status-marker--${props.status}`,
]);
</script>

<template>
  <span :class="classes" :data-status="status">{{ label }}</span>
</template>

<style scoped>
.gm-status-badge {
  white-space: nowrap;
  line-height: 1.4;
}

.gm-status-badge--neutral {
  color: var(--paper-300);
  border-color: var(--ink-600);
}

/* The text label carries the meaning; the glyph is decoration (empty
   alternative text keeps screen readers from announcing it). */
.gm-status-badge.status-marker--ok::before {
  content: "✓" / "";
}
.gm-status-badge.status-marker--warn::before {
  content: "▲" / "";
}
.gm-status-badge.status-marker--crit::before {
  content: "✕" / "";
}
.gm-status-badge--neutral::before {
  content: "‧" / "";
}
</style>
