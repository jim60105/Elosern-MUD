<script setup>
// An actual error state (gm-portal-s1-foundation): the operator sees the
// server's zh-TW message and its stable code verbatim. Actions are neutral
// (retry, go back) — seal-red is reserved for destructive actions.
// `compact` tightens it for an in-panel slot error; `live="off"` keeps a
// polled section's error from being re-announced on every refresh.
defineProps({
  title: { type: String, default: "發生錯誤" },
  message: { type: String, default: "" },
  code: { type: String, default: "" },
  compact: { type: Boolean, default: false },
  live: { type: String, default: "alert", validator: (value) => ["alert", "off"].includes(value) },
});
</script>

<template>
  <div class="gm-error" :class="{ 'gm-error--compact': compact }" :role="live === 'alert' ? 'alert' : null">
    <p class="gm-error__title">
      <span class="gm-error__glyph" aria-hidden="true">✕</span>{{ title }}
    </p>
    <p v-if="message" class="gm-error__message">{{ message }}</p>
    <p v-if="code" class="gm-error__code">
      <span class="gm-error__code-label">錯誤代碼</span>
      <code>{{ code }}</code>
    </p>
    <div v-if="$slots.actions" class="gm-error__actions"><slot name="actions" /></div>
  </div>
</template>

<style scoped>
.gm-error {
  display: grid;
  gap: var(--sp-3);
  padding: var(--sp-5);
  background: var(--ink-860);
  border: 1px solid var(--ink-700);
  border-left: 3px double var(--crit);
  border-radius: var(--radius);
}

.gm-error--compact {
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
}

.gm-error--compact .gm-error__title {
  font-size: var(--text-md);
}

.gm-error__title {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--paper-50);
}

.gm-error__glyph {
  color: var(--crit);
  font-family: var(--f-sans);
}

.gm-error__message {
  color: var(--paper-300);
}

.gm-error__code {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
}

.gm-error__code-label {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-error__code code {
  padding: 2px var(--sp-2);
  font-size: var(--text-sm);
  color: var(--paper-200);
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius-sm);
  user-select: all;
}

.gm-error__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin-top: var(--sp-1);
}
</style>
