<script setup>
// DetailFooter (handbook-primitives, design D1): the pinned action footer of a
// detail column, extracted from QuestDetail so the quest window and the
// handbook's CodexDetail share one footer. It renders an optional reason line
// and descriptor buttons in order, and emits `press(key)` for an enabled
// button only.
//
// A disabled button stays focusable (aria-disabled) and emits nothing; with
// `describedByReason` it points aria-describedby at the reason line. A button
// with a pressed state (`pressed !== null`) is a toggle: it renders
// aria-pressed and uses the native `disabled` attribute instead. The host
// moves focus through the exposed `focus(key)`.
import { useId } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";

const props = defineProps({
  reason: { type: String, default: null },
  // "plain" | "danger"
  reasonTone: { type: String, default: "plain" },
  // "alert" while a confirmation is armed.
  reasonRole: { type: String, default: null },
  reasonTestid: { type: String, default: null },
  // [{ key, label, tone: "plain"|"primary"|"ghost"|"danger", enabled = true,
  //    pressed = null, glyph = null, testid, describedByReason = false,
  //    spacerBefore = false }]
  buttons: { type: Array, default: () => [] },
  testid: { type: String, default: null },
});

const emit = defineEmits(["press"]);

const reasonId = `detail-footer-reason-${useId()}`;

const els = new Map();
function setEl(key, el) {
  if (el) els.set(key, el);
  else els.delete(key);
}

const isToggle = (button) => button.pressed !== null && button.pressed !== undefined;
const isEnabled = (button) => button.enabled !== false;
const isAriaDisabled = (button) => !isToggle(button) && !isEnabled(button);

function toneClass(button) {
  return button.tone && button.tone !== "plain" ? `detail-footer__btn--${button.tone}` : null;
}

function press(button) {
  if (!isEnabled(button)) return;
  emit("press", button.key);
}

function focus(key) {
  els.get(key)?.focus();
}

defineExpose({ focus });
</script>

<template>
  <footer class="detail-footer" :data-testid="testid || undefined">
    <p
      v-if="reason"
      :id="reasonId"
      class="detail-footer__why"
      :class="{ 'detail-footer__why--danger': reasonTone === 'danger' }"
      :role="reasonRole || undefined"
      :data-testid="reasonTestid || undefined"
    >{{ reason }}</p>
    <template v-for="button in buttons" :key="button.key">
      <span v-if="button.spacerBefore" class="detail-footer__spacer"></span>
      <button
        :ref="(el) => setEl(button.key, el)"
        type="button"
        class="detail-footer__btn"
        :class="[toneClass(button), { 'is-on': isToggle(button) && button.pressed, 'is-disabled': isAriaDisabled(button) }]"
        :aria-pressed="isToggle(button) ? String(!!button.pressed) : undefined"
        :disabled="isToggle(button) && !isEnabled(button)"
        :aria-disabled="isAriaDisabled(button) ? 'true' : undefined"
        :aria-describedby="isAriaDisabled(button) && button.describedByReason && reason ? reasonId : undefined"
        :data-testid="button.testid || undefined"
        @click="press(button)"
      >
        <svg v-if="button.glyph" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path :d="glyphPath(button.glyph)" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs(button.glyph)" />
        </svg>
        {{ button.label }}
      </button>
    </template>
  </footer>
</template>

<style scoped>
/* Moved unchanged from QuestDetail's `.quest-detail__actions` family. The
   border colour is the literal value of QuestDetail's --quest-detail-line, so
   the footer draws the same rule outside the quest detail. */
.detail-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-3);
  box-sizing: border-box;
  min-height: calc(64px * var(--ui-scale));
  padding: var(--sp-3) var(--sp-8);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.15), rgba(0, 0, 0, 0.4));
  border-top: 1px solid rgba(185, 154, 96, 0.28);
}

.detail-footer__spacer {
  flex: 1;
}

.detail-footer__why {
  margin: 0 auto 0 0;
  color: var(--paper-400);
  font-size: var(--text-sm);
}

.detail-footer__why--danger {
  color: var(--seal-400);
}

.detail-footer__btn {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-5);
  color: var(--paper-100);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.08em;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--motion-fast) ease, color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}

.detail-footer__btn svg {
  width: 1em;
  height: 1em;
}

.detail-footer__btn:hover:not(:disabled) {
  color: var(--paper-50);
  border-color: var(--gold-500);
}

.detail-footer__btn:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.detail-footer__btn:disabled,
.detail-footer__btn.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.detail-footer__btn.is-on {
  color: var(--gold-300);
  background: var(--gold-glow);
  border-color: var(--gold-500);
}

.detail-footer__btn.is-on svg {
  fill: rgba(228, 200, 142, 0.35);
}

.detail-footer__btn--primary {
  justify-content: center;
  min-width: calc(160px * var(--ui-scale));
  color: var(--paper-50);
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  border-color: var(--gold-500);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 0 14px var(--seal-glow);
}

.detail-footer__btn--primary:hover:not(:disabled):not(.is-disabled) {
  background: linear-gradient(180deg, var(--seal-500), var(--seal-600));
}

.detail-footer__btn--ghost {
  color: var(--paper-400);
  background: transparent;
  border-color: transparent;
}

.detail-footer__btn--ghost:hover:not(:disabled) {
  color: var(--seal-400);
  border-color: rgba(207, 68, 68, 0.4);
}

.detail-footer__btn--danger {
  color: var(--paper-50);
  background: var(--seal-700);
  border-color: var(--seal-500);
}

@media (prefers-reduced-motion: reduce) {
  .detail-footer__btn {
    transition: none;
  }
}
</style>
