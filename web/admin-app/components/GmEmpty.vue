<script setup>
// The empty state of a panel or table (gm-portal-s1-foundation): an actual
// "no data" state, never a placeholder for an undelivered feature.
defineProps({
  title: { type: String, default: "目前沒有資料" },
  message: { type: String, default: "" },
});
</script>

<template>
  <div class="gm-empty">
    <span class="gm-empty__ornament" aria-hidden="true"></span>
    <p class="gm-empty__title">{{ title }}</p>
    <p v-if="message" class="gm-empty__message">{{ message }}</p>
    <div v-if="$slots.actions" class="gm-empty__actions"><slot name="actions" /></div>
  </div>
</template>

<style scoped>
.gm-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-8) var(--sp-6);
  text-align: center;
}

.gm-empty__ornament {
  width: 60px;
  height: 22px;
  margin-bottom: var(--sp-2);
  background: var(--band-ornament) center / contain no-repeat;
  opacity: 0.6;
}

.gm-empty__title {
  font-family: var(--f-serif);
  font-size: var(--text-md);
  color: var(--paper-200);
}

.gm-empty__message {
  max-width: 36ch;
  font-size: var(--text-sm);
  color: var(--paper-500);
}

.gm-empty__actions {
  margin-top: var(--sp-3);
}
</style>
