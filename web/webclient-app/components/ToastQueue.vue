<script setup>
// Action-feedback toast queue (webclient-action-feedback D1/D2): a passive
// renderer over the store's client-local queue — zero local state. The store
// is the sole writer (`pushToast`/`dismissToast`); this component renders each
// entry's title (`.tt`, with the draft's leading icon) and optional subtitle
// (`.ts`), and a click dismisses that entry. Visuals mirror the redesign
// draft's `.toasts`/`.toast`/`.tt`/`.ts`/`.toast.crit` rules
// (docs/design/elosern-redesign/index.html:287-294) on repo tokens; the
// entrance reuses the formerly orphan `@keyframes elosern-toast-in`, so the
// motion level's token blocks cover it at the token level (D5). The queue is
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
      :class="{ crit: toast.tone === 'crit', 'toast--unlock': toast.tone === 'unlock' }"
      :role="toast.tone === 'crit' ? 'alert' : 'status'"
      :data-tone="toast.tone"
      :data-testid="`feedback-toast-${toast.id}`"
      @click="$emit('dismiss', toast.id)"
    >
      <div class="tt">
        <!-- The unlock notice (authored-dialogue-unread-notices) draws a
             four-point spark inside a ring: the same mark the choice list's
             unread pip echoes, so the notice and its rows read as one. -->
        <svg
          v-if="toast.tone === 'unlock'"
          class="ic ic--unlock"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          aria-hidden="true"
          data-icon="unlock-spark"
        >
          <circle cx="12" cy="12" r="9.2" opacity="0.55" />
          <path
            d="M12 5.2l1.55 5.25L18.8 12l-5.25 1.55L12 18.8l-1.55-5.25L5.2 12l5.25-1.55z"
            fill="currentColor"
            stroke-linejoin="round"
          />
        </svg>
        <svg
          v-else
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
      <ul v-if="toast.chips" class="toast__chips" data-testid="feedback-toast-chips">
        <li v-for="(chip, index) in toast.chips" :key="index" class="toast__chip">
          <span class="toast__chip-pip" aria-hidden="true"></span>{{ chip }}
        </li>
      </ul>
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
  top: calc(var(--header-h) + 12px * var(--ui-scale));
  right: calc(16px * var(--ui-scale));
  width: min(320px * var(--ui-scale), calc(100vw - 32px * var(--ui-scale)));
  /* Bounded above the bottom band and its command-line row, so a tall stack
     never covers the dock or the message window (webclient-avg-stage-shell). */
  max-height: calc(100dvh - var(--header-h) - var(--stage-content-bottom) - 24px * var(--ui-scale));
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: calc(8px * var(--ui-scale));
  pointer-events: none;
  z-index: calc(var(--z-surface-modal) + 100);
}
.toast {
  position: relative;
  background: var(--panel);
  backdrop-filter: blur(calc(8px * var(--ui-scale)));
  border: var(--line);
  border-left: calc(3px * var(--ui-scale)) solid var(--gold-500);
  border-radius: var(--radius);
  padding: calc(14px * var(--ui-scale)) calc(42px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(16px * var(--ui-scale));
  box-shadow: var(--shadow);
  font-size: var(--text-xs);
  pointer-events: auto;
  cursor: pointer;
  overflow-wrap: anywhere;
  animation: elosern-toast-in var(--motion-base) ease;
}
.toast .tt {
  font-weight: 600;
  color: var(--paper-50);
  display: flex;
  gap: calc(8px * var(--ui-scale));
  align-items: center;
  margin-bottom: 2px;
}
.toast .tt .ic {
  flex: none;
  width: calc(16px * var(--ui-scale));
  height: calc(16px * var(--ui-scale));
  color: var(--gold-400);
}
.toast .ts {
  color: var(--paper-300);
  font-size: var(--text-xs);
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

/* The dialogue unlock notice (authored-dialogue-unread-notices): a quiet
   status, never an alert. Its gold edge is doubled by a soft inner glow and
   the title sits in the warm gold of the choice list's unread pip; the newly
   opened topics follow as small framed chips, each led by the same diamond
   pip, so the notice reads as "these rows are new" without competing with
   the scene for attention. Shape (spark, pips, chips) carries the meaning,
   never colour alone. */
.toast--unlock {
  border-left-color: var(--gold-400);
  background:
    linear-gradient(90deg, rgba(228, 200, 142, 0.12), rgba(228, 200, 142, 0) 46%),
    var(--panel);
  box-shadow:
    var(--shadow),
    inset calc(1px * var(--ui-scale)) 0 0 rgba(238, 221, 180, 0.35);
}
.toast--unlock .tt {
  color: var(--gold-300);
  letter-spacing: 0.06em;
  text-shadow: 0 0 calc(8px * var(--ui-scale)) rgba(238, 221, 180, 0.25);
}
.toast--unlock .tt .ic--unlock {
  width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
  color: var(--gold-400);
  filter: drop-shadow(0 0 calc(4px * var(--ui-scale)) rgba(238, 221, 180, 0.45));
}
.toast__chips {
  list-style: none;
  margin: calc(8px * var(--ui-scale)) 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: calc(6px * var(--ui-scale));
}
.toast__chip {
  display: inline-flex;
  align-items: center;
  gap: calc(6px * var(--ui-scale));
  padding: calc(3px * var(--ui-scale)) calc(10px * var(--ui-scale)) calc(3px * var(--ui-scale)) calc(8px * var(--ui-scale));
  border: calc(1px * var(--ui-scale)) solid rgba(228, 200, 142, 0.45);
  border-radius: var(--radius-sm);
  background: rgba(228, 200, 142, 0.08);
  color: var(--paper-100);
  font-size: var(--text-xs);
  line-height: 1.4;
}
.toast__chip-pip {
  flex: none;
  width: calc(6px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  background: var(--gold-400);
  transform: rotate(45deg);
  box-shadow: 0 0 calc(4px * var(--ui-scale)) rgba(238, 221, 180, 0.6);
}

.toast__dismiss {
  position: absolute;
  top: calc(6px * var(--ui-scale));
  right: calc(6px * var(--ui-scale));
  width: calc(30px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--paper-300);
  font-size: var(--text-xl);
  cursor: pointer;
}
.toast__dismiss:hover { color: var(--gold-400); background: var(--gold-glow); }
.toast__dismiss:focus-visible { outline: 2px solid var(--gold-400); }
</style>
