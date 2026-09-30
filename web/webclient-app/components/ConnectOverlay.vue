<script setup>
// Connection overlay: the full-viewport pre-connection and waiting screen,
// and the disconnect notice. A non-dismissible state surface (a polite live
// region) shown for every transport status that is not "ready", mirroring
// the legacy offline-overlay semantics and the D10 text console status
// vocabulary. The status line pairs a glyph with a text label, so state is
// never conveyed by color alone. No props beyond the status slice; it emits
// no events (the store/transport owns reconnection, C3).
const STATUS_TEXT = {
  connecting: "● 連線中…",
  waiting: "◐ 等待登入…",
  offline: "○ 連線中斷",
  ready: "就緒",
};

defineProps({
  status: {
    type: String,
    default: "connecting",
    validator: (value) =>
      ["connecting", "waiting", "offline", "ready"].includes(value),
  },
});
</script>

<template>
  <section
    v-if="status !== 'ready'"
    class="elosern connect-overlay"
    role="status"
    aria-live="polite"
    aria-atomic="true"
    data-testid="connect-overlay"
    :data-status="status"
  >
    <div class="connect-overlay__wordmark" aria-hidden="true">ELOSERN</div>
    <div class="connect-overlay__brand" data-testid="connect-overlay-brand">
      伊洛瑟恩
    </div>
    <div class="connect-overlay__status" data-testid="connect-overlay-status">
      {{ STATUS_TEXT[status] }}
    </div>
  </section>
</template>

<style>
.connect-overlay {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--sp-4);
  box-sizing: border-box;
  padding: calc(32px * var(--ui-scale));
  text-align: center;
  background: radial-gradient(ellipse at 50% 40%, var(--ink-780), var(--ink-950) 70%);
  color: var(--paper-100);
}

.connect-overlay::before,
.connect-overlay::after {
  content: "";
  width: min(320px * var(--ui-scale), 80%);
  height: 1px;
  margin: calc(20px * var(--ui-scale)) 0;
  background: linear-gradient(90deg, transparent, var(--gold-500), transparent);
}

.connect-overlay__wordmark {
  color: var(--gold-400);
  font: clamp(32px * var(--ui-scale), 6vw, 68px * var(--ui-scale))/1.2 var(--f-serif);
  letter-spacing: 0.18em;
  max-width: 100%;
  overflow-wrap: anywhere;
}

.connect-overlay__brand {
  font-family: var(--f-serif);
  font-size: var(--text-xl);
  letter-spacing: 0.2em;
  color: var(--paper-50);
}

.connect-overlay__status {
  font-family: var(--f-sans);
  font-size: var(--text-base);
  margin-top: calc(24px * var(--ui-scale));
  color: var(--gold-400);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: calc(12px * var(--ui-scale)) calc(24px * var(--ui-scale));
  background: var(--panel);
}

.connect-overlay[data-status="offline"] .connect-overlay__status {
  color: var(--warn);
  border-color: var(--warn);
  border-style: dashed;
}
</style>
