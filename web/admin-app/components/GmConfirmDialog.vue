<script setup>
// A modal confirmation (gm-portal-s5-saves): the native <dialog> in the top
// layer (showModal gives an inert background), `role="alertdialog"`, initial
// focus on 取消, focus returned to the opener on close. The confirm control
// names its consequence; `danger` paints it in seal ink — seal-red stays
// reserved for destructive or state-changing actions. Backdrop clicks are
// ignored and Esc cancels unless a request is in flight (`busy`), so an
// operator can never dismiss a decision half-sent. Errors from the action
// render inside the dialog (the `error` slot), which then stays open.
import { nextTick, onBeforeUnmount, ref, useId, watch } from "vue";

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  confirmLabel: { type: String, required: true },
  busyLabel: { type: String, default: "送出中…" },
  cancelLabel: { type: String, default: "取消" },
  danger: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  // Where focus goes on close when the opener left the DOM (a CSS selector).
  fallbackFocus: { type: String, default: "" },
});

const emit = defineEmits(["confirm", "cancel"]);

const id = useId();
const titleId = `gm-confirm-title-${id}`;
const bodyId = `gm-confirm-body-${id}`;
const dialog = ref(null);
const cancelButton = ref(null);
let opener = null;
let shown = false;

function show() {
  const element = dialog.value;
  if (!element || shown) return;
  shown = true;
  opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  if (typeof element.showModal === "function") element.showModal();
  else element.setAttribute("open", "");
  document.documentElement.classList.add("gm-scroll-locked");
  nextTick(() => cancelButton.value?.focus());
}

function hide() {
  if (!shown) return;
  shown = false;
  const element = dialog.value;
  if (element?.open) {
    if (typeof element.close === "function") element.close();
    else element.removeAttribute("open");
  }
  document.documentElement.classList.remove("gm-scroll-locked");
  let target = opener?.isConnected ? opener : null;
  if (!target && props.fallbackFocus) {
    target = document.querySelector(props.fallbackFocus);
    if (target && !target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
  }
  opener = null;
  target?.focus?.();
}

function requestCancel() {
  if (!props.busy) emit("cancel");
}

function onCancel(event) {
  // The browser's Esc path: never let it close the dialog behind Vue's back.
  event.preventDefault();
  requestCancel();
}

watch(
  () => props.open,
  (open) => nextTick(() => (open ? show() : hide())),
  { immediate: true },
);

onBeforeUnmount(() => {
  if (shown) document.documentElement.classList.remove("gm-scroll-locked");
});
</script>

<template>
  <dialog
    ref="dialog"
    class="gm-confirm"
    :class="{ 'gm-confirm--danger': danger }"
    role="alertdialog"
    aria-modal="true"
    :aria-labelledby="titleId"
    :aria-describedby="bodyId"
    :aria-busy="busy ? 'true' : null"
    @cancel="onCancel"
  >
    <div v-if="open" class="gm-confirm__frame">
      <header class="gm-confirm__header">
        <span class="gm-confirm__seal" aria-hidden="true"></span>
        <h2 :id="titleId" class="gm-confirm__title">{{ title }}</h2>
      </header>
      <div :id="bodyId" class="gm-confirm__body"><slot /></div>
      <div v-if="$slots.error" class="gm-confirm__error"><slot name="error" /></div>
      <footer class="gm-confirm__footer">
        <button ref="cancelButton" type="button" class="ui-btn" :disabled="busy" @click="requestCancel">
          {{ cancelLabel }}
        </button>
        <button
          type="button"
          class="ui-btn"
          :class="danger ? 'ui-btn--danger gm-confirm__go' : 'ui-btn--primary'"
          :disabled="busy"
          data-confirm
          @click="emit('confirm')"
        >
          {{ busy ? busyLabel : confirmLabel }}
        </button>
      </footer>
    </div>
  </dialog>
</template>

<style scoped>
.gm-confirm {
  width: min(36rem, calc(100vw - 2 * var(--sp-4)));
  max-height: calc(100dvh - 2 * var(--sp-8));
  padding: 0;
  overflow: auto;
  color: var(--paper-200);
  background: var(--ink-860);
  border: var(--line);
  border-top: 1px solid var(--gold-600);
  border-radius: var(--radius);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--gold-500) 22%, transparent),
    0 28px 80px -24px rgba(0, 0, 0, 0.95);
}

.gm-confirm--danger {
  border-top-color: var(--seal-600);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--seal-500) 30%, transparent),
    0 28px 80px -24px rgba(0, 0, 0, 0.95);
}

.gm-confirm[open] {
  animation: gm-confirm-in var(--motion-base) var(--ease-standard);
}

.gm-confirm::backdrop {
  background: color-mix(in srgb, var(--ink-950) 72%, transparent);
  backdrop-filter: blur(2px);
}

@keyframes gm-confirm-in {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.985);
  }
}

@media (prefers-reduced-motion: reduce) {
  .gm-confirm[open] {
    animation: none;
  }
}

.gm-confirm__frame {
  display: grid;
  gap: var(--sp-4);
  padding: var(--sp-6);
}

.gm-confirm__header {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

/* The diamond seal of GmPanel; a danger decision wears it in seal-red. */
.gm-confirm__seal {
  flex: none;
  width: 8px;
  height: 8px;
  background: var(--gold-500);
  transform: rotate(45deg);
}

.gm-confirm--danger .gm-confirm__seal {
  background: var(--seal-500);
  box-shadow: 0 0 0 3px var(--seal-glow);
}

.gm-confirm__title {
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  font-weight: 600;
  line-height: 1.35;
  color: var(--paper-50);
}

.gm-confirm__body {
  display: grid;
  gap: var(--sp-4);
  color: var(--paper-300);
}

.gm-confirm__footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--sp-2);
  padding-top: var(--sp-4);
  border-top: 1px dashed var(--ink-700);
}

/* The decisive danger action reads stronger than a row-level danger. */
.gm-confirm__go {
  font-weight: 600;
  border-color: var(--seal-600);
}

.gm-confirm :is(button, a, summary):focus-visible {
  outline: none;
  box-shadow: var(--focus);
}
</style>
