<script setup>
// Unread marker over the narrative feed: states how many lines arrived while
// the reader was not at the bottom, with a labeled jump-to-latest control.
// Preserved hooks: the `#narrative-unread` live region (role=status, polite,
// atomic, data-count) and the `.narrative-unread-button` control (Phase-0
// audit §2.3). The wrapper stays in the DOM at count 0 (hidden, no empty
// pill) so the live region can announce count changes. Emits `jump` on
// activation; the owning feed restores focus to the narrative pane before the
// marker hides (focus never drops into a hidden element).
defineProps({
  count: { type: Number, default: 0 },
});

defineEmits(["jump"]);
</script>

<template>
  <div
    id="narrative-unread"
    class="narrative-unread"
    role="status"
    aria-live="polite"
    aria-atomic="true"
    :data-count="count"
    :data-visible="count > 0"
    data-testid="unread-indicator"
  >
    <button
      v-if="count > 0"
      type="button"
      class="narrative-unread-button"
      data-testid="unread-indicator-button"
      @click="$emit('jump')"
    >
      ↓ {{ count }} 則新訊息（點擊返回最新）
    </button>
  </div>
</template>

<style>
/* Sticky at the top of the narrative scroll area (like the legacy marker):
   visible exactly while unread lines exist, hidden at count 0 (no empty
   pill). The live-region wrapper stays in the DOM at all times. */
.narrative-unread {
  position: sticky;
  top: 0;
  z-index: 5;
  float: right;
  width: fit-content;
  margin: var(--sp-2) var(--sp-4) 0;
  pointer-events: none;
}

.narrative-unread[data-visible="false"],
.narrative-unread[data-count="0"] {
  display: none;
}

.narrative-unread [data-testid="unread-indicator-button"] {
  pointer-events: auto;
}

.narrative-unread-button {
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-50);
  background: var(--seal-600);
  border: 1px solid var(--seal-400);
  border-radius: 999px;
  padding: 4px var(--sp-3);
  cursor: pointer;
  box-shadow: var(--shadow);
}

.narrative-unread-button:hover {
  background: var(--seal-500);
}
</style>
