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
  background: var(--ink-950);
  color: var(--paper-100);
}

.connect-overlay__brand {
  font-family: var(--f-display);
  font-size: 44px;
  letter-spacing: 0.2em;
  color: var(--paper-50);
}

.connect-overlay__status {
  font-family: var(--f-mono);
  font-size: var(--text-body);
  color: var(--paper-500);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: 2px var(--sp-3);
}

.connect-overlay[data-status="offline"] .connect-overlay__status {
  color: var(--warn);
  border-color: var(--warn);
  border-style: dashed;
}
</style>
