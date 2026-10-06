<script setup>
// A titled ledger card (gm-portal-s1-foundation): the content unit of every
// GM page. `flush` drops the body padding so a table's rules run edge to edge.
import { useId } from "vue";

defineProps({
  title: { type: String, required: true },
  description: { type: String, default: "" },
  flush: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
});

const headingId = `gm-panel-${useId()}`;
</script>

<template>
  <section class="gm-panel" :aria-labelledby="headingId">
    <header class="gm-panel__header">
      <div class="gm-panel__heading">
        <h2 :id="headingId" class="gm-panel__title">{{ title }}</h2>
        <p v-if="description" class="gm-panel__description">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="gm-panel__actions"><slot name="actions" /></div>
    </header>
    <div class="gm-panel__body" :class="{ 'gm-panel__body--flush': flush }" :aria-busy="busy ? 'true' : null">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.gm-panel {
  min-width: 0;
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--gold-500) 22%, transparent),
    var(--shadow);
}

.gm-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-4) var(--sp-5);
  border-bottom: 1px solid var(--ink-700);
}

.gm-panel__title {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  font-weight: 600;
  line-height: 1.3;
  color: var(--paper-100);
}

/* The seal-like diamond, drawn in gold (seal-red stays destructive-only). */
.gm-panel__title::before {
  content: "";
  flex: none;
  width: 6px;
  height: 6px;
  background: var(--gold-500);
  transform: rotate(45deg);
}

.gm-panel__description {
  margin-top: var(--sp-1);
  padding-left: calc(6px + var(--sp-3));
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-panel__actions {
  display: flex;
  gap: var(--sp-2);
}

.gm-panel__body {
  padding: var(--sp-5);
}

.gm-panel__body--flush {
  padding: 0;
}
</style>
