<script setup>
// Action-feedback toast queue (webclient-action-feedback D1/D2): a passive
// renderer over the store's client-local queue — zero local state. The store
// is the sole writer (`pushToast`/`dismissToast`); this component renders each
// entry's title (`.tt`, with the draft's leading icon) and optional subtitle
// (`.ts`), and a click dismisses that entry. Visuals mirror the redesign
// draft's `.toasts`/`.toast`/`.tt`/`.ts`/`.toast.crit` rules
// (docs/design/elosern-redesign/index.html:287-294) on repo tokens; the
// entrance reuses the formerly orphan `@keyframes elosern-toast-in`, so the
// reduced-motion token block covers it at the token level (D5). The queue is
// fixed-positioned above every product overlay (the modal tier + 100, the
// `.inventory-confirm` precedent) so a concept failure is visible while the
// creation overlay is mounted; only the offline overlay (the reserved
// `--z-offline` tier) intentionally outranks it.
defineProps({
  toasts: { type: Array, default: () => [] },
});

defineEmits(["dismiss"]);
</script>

<template>
  <div class="toasts" data-testid="feedback-toast-queue">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      class="toast"
      :class="{ crit: toast.tone === 'crit' }"
      :role="toast.tone === 'crit' ? 'alert' : 'status'"
      :data-tone="toast.tone"
      :data-testid="`feedback-toast-${toast.id}`"
      @click="$emit('dismiss', toast.id)"
    >
      <div class="tt">
        <svg
          class="ic"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          aria-hidden="true"
        >
          <path :d="toast.tone === 'crit' ? 'M6 6l12 12M6 18L18 6' : 'M5 13l4 4L19 7'" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        {{ toast.title }}
      </div>
      <div v-if="toast.sub" class="ts">{{ toast.sub }}</div>
      <button class="toast__dismiss" type="button" aria-label="關閉通知" @click.stop="$emit('dismiss', toast.id)">×</button>
    </div>
  </div>
</template>

<style scoped>
/* Ported from the redesign draft (docs/design/elosern-redesign/index.html:
   287-294), with the draft's stage-local `z-index: 6` replaced by the shared
   modal tier so the queue outranks every product overlay, and the draft's
   private `toastIn` entrance replaced by the repo motion system's
   `elosern-toast-in`. */
.toasts {
  position: fixed;
  top: calc(var(--header-h) + 12px);
  right: 16px;
  width: min(320px, calc(100vw - 32px));
  max-height: calc(100dvh - var(--header-h) - var(--command-line-h) - 24px);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
  z-index: calc(var(--z-surface-modal) + 100);
}
.toast {
  position: relative;
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: var(--line);
  border-left: 3px solid var(--gold-500);
  border-radius: 9px;
  padding: 14px 42px 14px 16px;
  box-shadow: var(--shadow);
  font-size: 12px;
  pointer-events: auto;
  cursor: pointer;
  overflow-wrap: anywhere;
  animation: elosern-toast-in var(--motion-base) ease;
}
.toast .tt {
  font-weight: 600;
  color: var(--paper-50);
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 2px;
}
.toast .tt .ic {
  flex: none;
  width: 16px;
  height: 16px;
  color: var(--gold-400);
}
.toast .ts {
  color: var(--paper-300);
  font-size: 12px;
  line-height: 1.6;
}
.toast.crit {
  border-left-color: var(--seal-500);
}
.toast.crit .tt {
  color: var(--crit);
}
.toast.crit .tt .ic {
  color: var(--seal-400);
}

.toast__dismiss {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--paper-300);
  font-size: 20px;
  cursor: pointer;
}
.toast__dismiss:hover { color: var(--gold-400); background: var(--gold-glow); }
.toast__dismiss:focus-visible { outline: 2px solid var(--gold-400); }
</style>
