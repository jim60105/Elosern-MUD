<script setup>
// DockMenuItem (B2 action family): one cell of the action dock's framed
// grid. Passive — `focused` and `enabled` are prop slices the parent (the
// store-backed shell at C3) owns; the click pointer path emits `focus` on
// every cell and `activate` on enabled cells (the keyboard path is the
// preserved KeyboardRouter's job at C2/C4).
//
// Preserved contract: the `data-item-key` row identity (`action-`/`target-`
// keys are component-owned per design D5), `role="option"` inside the
// `role="listbox"` grid, the disabled cell keeps the server reason readable
// (suffix text plus a hidden `aria-describedby` note), and focus is shown by
// a seal-red fill plus a leading glyph — never by color alone.
const props = defineProps({
  itemKey: { type: String, required: true },
  label: { type: String, required: true },
   enabled: { type: Boolean, default: true },
   selected: { type: Boolean, default: false },
   reason: { type: String, default: null },
   focused: { type: Boolean, default: false },
   rowId: { type: String, required: true },
});

const emit = defineEmits(["focus", "activate"]);

function onActivate() {
  // Pointer parity with the preserved keyboard bridge: a click on any cell
  // moves the dock focus (so a disabled cell's explanation can be read),
  // while activation — the dispatch intent — happens only for enabled cells
  // (UI design §5.3).
  emit("focus", props.itemKey);
  if (props.enabled) {
    emit("activate", props.itemKey);
  }
}
</script>

<template>
  <button
    :id="rowId"
    type="button"
    role="option"
    tabindex="-1"
    class="dock-menu-item"
    :class="{
      'dock-menu-item--focused': focused,
      'dock-menu-item--disabled': !enabled,
    }"
    :aria-selected="focused"
    :aria-disabled="!enabled"
    :aria-describedby="!enabled && reason ? rowId + '-reason' : null"
    :data-item-key="itemKey"
    data-testid="dock-item"
    @click="onActivate"
  >
    <span
      v-if="selected"
      class="dock-menu-item__checked"
      aria-hidden="true"
    >✓</span>
    <span class="dock-menu-item__label">{{ label }}</span
    ><span
      v-if="!enabled"
      class="dock-menu-item__unavailable"
      aria-hidden="true"
    >（無法使用）</span>
    <span
      v-if="!enabled && reason"
      :id="rowId + '-reason'"
      class="visually-hidden"
    >{{ reason }}</span>
  </button>
</template>

<style scoped>
.dock-menu-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-1);
  box-sizing: border-box;
  min-width: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  line-height: 1.4;
  text-align: center;
  white-space: nowrap;
  cursor: pointer;
}

/* Focus is a seal-red fill plus a leading glyph, never color alone. */
.dock-menu-item--focused {
  background: var(--seal-600);
  border-color: var(--seal-500);
  color: var(--paper-50);
  box-shadow: var(--focus);
}

/* The focus caret is a leading glyph via ::before (not color alone), so the
   managed-browser contract `getComputedStyle(el, '::before').content` sees
   the "▶" glyph. */
.dock-menu-item--focused::before {
  content: "▶";
  color: var(--gold-400);
  font-size: 0.8em;
}

/* The AREA selection marker: a green check prefix on a selected candidate,
   distinct from the gold focus caret (not color alone — it's a glyph). */
.dock-menu-item__checked {
  color: var(--ok);
  font-size: 0.9em;
  font-weight: 700;
}

/* Disabled: dim text, dashed frame, dimmed fill — the `（無法使用）`
   suffix and the hidden reason note carry the state without color. */
.dock-menu-item--disabled {
  color: var(--paper-500);
  background: var(--ink-900);
  border-style: dashed;
  border-color: var(--ink-600);
  cursor: default;
}

.dock-menu-item__unavailable {
  color: var(--paper-700);
  font-size: 0.85em;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}
</style>
