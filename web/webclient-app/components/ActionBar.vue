<script setup>
// ActionBar (webclient-window-primitives, design §3.4/§9): the bar pinned to
// the bottom of a window's detail column. The left slot shows state
// feedback only — a committed reason the caller passes (`reason`, e.g. the
// combat 戰鬥中無法交換物品 when the give controls are absent) and the
// committed reason of every disabled control — and the right end holds the
// buttons. The bar authors no explanatory rule text of its own.
//
// A disabled control keeps focus (`aria-disabled`, like IconTabs) and is
// described by its own reason; activating it emits nothing. An enabled
// control emits `action(key)`.
import { computed, useId } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";

const props = defineProps({
  // [{ key, label, enabled = true, reason?: string | null,
  //    tone?: "primary" | "gold" | "ghost", glyph?, busy? }]
  // `busy` marks a control whose request is in flight (aria-busy).
  actions: { type: Array, default: () => [] },
  // A committed reason shown on its own: a string or { code, message }.
  reason: { type: [String, Object], default: null },
});

const emit = defineEmits(["action"]);

const uid = useId();

const isEnabled = (action) => action.enabled !== false;
const textOf = (reason) => (typeof reason === "string" ? reason : (reason?.message ?? ""));

// Every distinct reason, in order: the caller's own first, then each
// disabled control's. Each one has an id its controls are described by.
const reasons = computed(() => {
  const list = [];
  const add = (text, code) => {
    if (!text || list.some((entry) => entry.text === text)) return;
    list.push({ text, code: code ?? null, id: `action-bar-${uid}-reason-${list.length}` });
  };
  if (props.reason) add(textOf(props.reason), typeof props.reason === "object" ? props.reason.code : null);
  for (const action of props.actions) {
    if (!isEnabled(action) && action.reason) add(textOf(action.reason), action.reason?.code);
  }
  return list;
});

function describedBy(action) {
  if (isEnabled(action) || !action.reason) return undefined;
  return reasons.value.find((entry) => entry.text === textOf(action.reason))?.id;
}

function activate(action) {
  if (!isEnabled(action)) return;
  emit("action", action.key);
}
</script>

<template>
  <div class="action-bar" data-testid="action-bar">
    <div class="action-bar__lead">
      <p
        v-for="entry in reasons"
        :id="entry.id"
        :key="entry.id"
        class="action-bar__reason"
        data-testid="action-bar__reason"
        :data-reason-code="entry.code || undefined"
      >{{ entry.text }}</p>
      <slot name="lead" />
    </div>
    <slot />
    <button
      v-for="action in actions"
      :key="action.key"
      type="button"
      class="action-bar__btn"
      :class="[action.tone ? `action-bar__btn--${action.tone}` : null, { 'is-disabled': !isEnabled(action) }]"
      :data-testid="`action-bar__btn--${action.key}`"
      :aria-disabled="isEnabled(action) ? undefined : 'true'"
      :aria-describedby="describedBy(action)"
      :aria-busy="action.busy ? 'true' : undefined"
      @click="activate(action)"
    >
      <svg v-if="action.glyph && glyphPath(action.glyph)" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path :d="glyphPath(action.glyph)" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs(action.glyph)" />
      </svg>
      {{ action.label }}
    </button>
  </div>
</template>

<style scoped>
/* The approved prototype's `.pm-bar` / `.pm-btn`
   (docs/design/party-member-management/prototype.css). */
.action-bar {
  --action-bar-line: rgba(185, 154, 96, 0.28);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-3);
  margin-top: var(--sp-4);
  padding-top: var(--sp-3);
  border-top: calc(1px * var(--ui-scale)) solid var(--action-bar-line);
}

.action-bar__lead {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  min-width: 0;
  margin-right: auto;
  color: var(--paper-400);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
}

.action-bar__reason {
  margin: 0;
  color: var(--paper-500);
  font-size: var(--text-xs);
}

.action-bar__btn {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  flex: none;
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-200);
  font: var(--text-sm) var(--f-sans);
  background: transparent;
  border: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: color var(--motion-fast) ease, border-color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}

.action-bar__btn svg {
  width: 1em;
  height: 1em;
}

.action-bar__btn:hover {
  color: var(--paper-50);
  border-color: var(--gold-500);
}

.action-bar__btn:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.action-bar__btn--primary {
  color: var(--paper-50);
  background: var(--seal-500);
  border-color: var(--seal-500);
}

.action-bar__btn--primary:hover {
  background: var(--seal-400);
  border-color: var(--seal-400);
}

.action-bar__btn--gold {
  color: var(--gold-300);
  border-color: var(--gold-600);
}

.action-bar__btn--ghost {
  color: var(--paper-500);
  border-color: transparent;
}

.action-bar__btn.is-disabled,
.action-bar__btn.is-disabled:hover {
  color: var(--paper-700);
  background: transparent;
  border-style: dashed;
  border-color: var(--ink-600);
  cursor: not-allowed;
}

@media (prefers-reduced-motion: reduce) {
  .action-bar__btn {
    transition: none;
  }
}
</style>
