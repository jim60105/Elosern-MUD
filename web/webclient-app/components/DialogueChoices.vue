<script setup>
// DialogueChoices (webclient-dialogue-choices-overlay D5; AVG stage design
// §8.2): the conversation's choice list, centred over the stage in the
// `choices` anchor once the session line is fully read. Rows, in order: one
// pick per committed `dialogue.choices` entry (digit badge 1–N), then
// `⌨ 自由對話`, `↦ 移動…`, and `✕ 結束對話`. `↦ 移動…` swaps the rows for the
// committed scene overview's exits (direction glyph and destination, a
// disabled exit keeping its server-authored reason) plus a back row.
//
// One keyboard composite, one tab stop: DOM focus rests on the menu
// container, which names its active row through `aria-activedescendant`
// (the dock's pattern). ArrowUp / ArrowDown wrap, Home / End jump, Enter /
// Space activate (a held repeat never does), digits 1–N activate pick N,
// and Escape leaves the exits. Every handled key is consumed before it can
// bubble to the document keyboard bridge; `/`, Tab, and every other key
// pass through untouched. A pointer activation focuses the list and runs
// the same activation path as Enter.
//
// Passive: activation calls `beforeActivate` (the shell parks focus on the
// message page so the list's removal never drops it) and emits the row's
// intent; the parent owns every dispatch.
import { computed, nextTick, ref, useId, watch } from "vue";
import { directionGlyph, disabledRowReason, exitLabel } from "./dock-exits.js";

const props = defineProps({
  // The dialogue view model's pick rows (`dialogueViewModel(...).picks`).
  picks: { type: Array, default: () => [] },
  // The committed scene overview's exit items, in its order.
  exits: { type: Array, default: () => [] },
  // The committed `localMapModel`, for exit destination names.
  localMap: { type: Object, default: null },
  // A mutation is in flight or awaiting its revision: no activation runs.
  // A component-level safety net: AppClient never renders the list while a
  // dispatch is in flight, so the live wiring does not reach it.
  locked: { type: Boolean, default: false },
  // Called before every emitted activation.
  beforeActivate: { type: Function, default: null },
});

const emit = defineEmits(["pick", "freeform", "move", "leave"]);

const listRef = ref(null);
const scrollRef = ref(null);
const idPrefix = useId();
const view = ref("choices");
const activeIndex = ref(0);

const rows = computed(() => {
  if (view.value === "exits") {
    const exitRows = props.exits.map((item, index) => {
      const enabled = item.enabled !== false;
      return {
        kind: "exit",
        key: `exit-${item.key ?? index}`,
        testId: "dialogue-exit-row",
        badge: directionGlyph(item.direction) || "↦",
        label: exitLabel(item, props.localMap),
        enabled,
        reason: enabled ? null : disabledRowReason(item),
        item,
      };
    });
    return [
      ...exitRows,
      { kind: "back", key: "back", testId: "dialogue-exits-back", badge: "↩", label: "返回對話", enabled: true },
    ];
  }
  return [
    ...props.picks.map((pick, index) => ({
      kind: "pick",
      key: pick.key,
      testId: "dialogue-pick",
      badge: String(index + 1),
      label: pick.label,
      keywordId: pick.payload ? pick.payload.keyword_id : undefined,
      enabled: true,
      pick,
    })),
    { kind: "freeform", key: "freeform", testId: "dialogue-freeform", badge: "⌨", label: "自由對話", enabled: true },
    { kind: "move", key: "move", testId: "dialogue-move", badge: "↦", label: "移動…", enabled: true },
    { kind: "leave", key: "leave", testId: "dialogue-exit", badge: "✕", label: "結束對話", enabled: true },
  ];
});

// The trailing rows of the choice view open with a divider after the picks.
const firstTrailing = computed(() => (view.value === "choices" ? props.picks.length : props.exits.length));

function rowId(index) {
  return `${idPrefix}-row-${index}`;
}

function reasonId(index) {
  return `${idPrefix}-reason-${index}`;
}

// A committed update that shortens the rows keeps the active row in range.
watch(
  () => rows.value.length,
  (length) => {
    if (activeIndex.value > length - 1) {
      activeIndex.value = Math.max(0, length - 1);
    }
  },
);

function setActive(index) {
  activeIndex.value = index;
  void nextTick(() => {
    const el = Array.from(scrollRef.value?.children || []).find((child) => child.id === rowId(index));
    el?.scrollIntoView?.({ block: "nearest" });
  });
}

function showView(next, index) {
  view.value = next;
  setActive(index);
}

function activate(index) {
  const row = rows.value[index];
  if (!row) {
    return;
  }
  // The exits swap and the way back are local: they dispatch nothing.
  if (row.kind === "move") {
    showView("exits", 0);
    return;
  }
  if (row.kind === "back") {
    showView("choices", props.picks.length + 1);
    return;
  }
  if (props.locked || !row.enabled) {
    return;
  }
  props.beforeActivate?.();
  if (row.kind === "pick") {
    emit("pick", row.pick);
  } else if (row.kind === "freeform") {
    emit("freeform");
  } else if (row.kind === "leave") {
    emit("leave");
  } else if (row.kind === "exit") {
    emit("move", row.item);
  }
}

function consume(event) {
  event.preventDefault();
  event.stopPropagation();
}

function onKeydown(event) {
  if (event.ctrlKey || event.altKey || event.metaKey) {
    return;
  }
  const count = rows.value.length;
  const key = event.key;
  if (key === "ArrowDown" || key === "ArrowUp") {
    consume(event);
    if (count > 0) {
      const step = key === "ArrowDown" ? 1 : -1;
      setActive((activeIndex.value + step + count) % count);
    }
    return;
  }
  if (key === "Home" || key === "End") {
    consume(event);
    if (count > 0) {
      setActive(key === "Home" ? 0 : count - 1);
    }
    return;
  }
  // Shift+Enter / Shift+Space are not the list's activation keys: they pass
  // through like every other modified key.
  if ((key === "Enter" || key === " ") && !event.shiftKey) {
    consume(event);
    if (!event.repeat) {
      activate(activeIndex.value);
    }
    return;
  }
  if (key === "Escape") {
    if (view.value === "exits") {
      consume(event);
      showView("choices", props.picks.length + 1);
    }
    return;
  }
  if (view.value === "choices" && key.length === 1 && key >= "1" && key <= "9") {
    const index = Number(key) - 1;
    if (index < props.picks.length) {
      consume(event);
      if (!event.repeat) {
        setActive(index);
        activate(index);
      }
    }
  }
}

function onRowClick(index) {
  listRef.value?.focus({ preventScroll: true });
  setActive(index);
  activate(index);
}

function focus() {
  listRef.value?.focus({ preventScroll: true });
}

defineExpose({ focus });
</script>

<template>
  <div
    ref="listRef"
    class="dialogue-choices"
    role="menu"
    :aria-label="view === 'exits' ? '移動：選擇出口' : '對話選項'"
    tabindex="0"
    data-testid="dialogue-choices"
    :data-view="view"
    :aria-activedescendant="rows.length ? rowId(activeIndex) : null"
    @keydown="onKeydown"
  >
    <div v-if="view === 'exits'" class="dialogue-choices__caption" aria-hidden="true">移動</div>
    <div ref="scrollRef" class="dialogue-choices__rows">
    <div
      v-for="(row, index) in rows"
      :id="rowId(index)"
      :key="`${view}-${row.key}`"
      class="dialogue-choices__row"
      :class="[
        `dialogue-choices__row--${row.kind}`,
        {
          'dialogue-choices__row--active': index === activeIndex,
          'dialogue-choices__row--trailing': index === firstTrailing,
        },
      ]"
      role="menuitem"
      :data-testid="row.testId"
      :data-keyword-id="row.keywordId"
      :data-active="index === activeIndex ? 'true' : 'false'"
      :aria-disabled="row.enabled ? null : 'true'"
      :aria-describedby="row.reason ? reasonId(index) : null"
      @click="onRowClick(index)"
    >
      <span class="dialogue-choices__badge" aria-hidden="true" :data-badge="row.badge">
        <!-- The keyboard glyph draws tiny in the loaded text faces, so the
             free row's ⌨ badge is drawn as a small keyboard. -->
        <svg
          v-if="row.kind === 'freeform'"
          class="dialogue-choices__badge-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
        >
          <rect x="2.5" y="6" width="19" height="12" rx="2.2" />
          <path d="M6.5 10h.01M10 10h.01M14 10h.01M17.5 10h.01M8 14h8" stroke-width="2" />
        </svg>
        <template v-else>{{ row.badge }}</template>
      </span>
      <span class="dialogue-choices__text">
        <span class="dialogue-choices__label">{{ row.label }}</span>
        <span
          v-if="row.reason"
          :id="reasonId(index)"
          class="dialogue-choices__reason"
          data-testid="dialogue-exit-reason"
        >{{ row.reason }}</span>
      </span>
    </div>
    </div>
  </div>
</template>

<style>
/* The choice card (design D6): the reference's caption-panel treatment. */
.dialogue-choices {
  position: relative;
  box-sizing: border-box;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(120% 60% at 50% 0%, rgba(185, 154, 96, 0.1), transparent 70%),
    linear-gradient(180deg, rgba(27, 25, 29, 0.95), rgba(12, 13, 17, 0.95));
  border: 1px solid rgba(185, 154, 96, 0.45);
  border-radius: var(--radius);
  box-shadow:
    var(--shadow-lg),
    inset 0 0 0 1px rgba(0, 0, 0, 0.55),
    inset 0 1px 0 1px rgba(238, 221, 180, 0.06);
  backdrop-filter: blur(6px);
  outline: none;
  pointer-events: auto;
}

/* The exits view's quiet caption: it names what the rows now are. */
.dialogue-choices__caption {
  flex: none;
  padding: 12px 20px 0;
  font: 12px/1.4 var(--f-sans);
  letter-spacing: 0.3em;
  color: var(--gold-500);
  text-align: center;
}

.dialogue-choices__caption + .dialogue-choices__rows {
  padding-top: 8px;
}

/* Keyboard focus on the one tab stop: the card keeps its drop shadow (the
   global `:focus-visible` ring would replace it with a hard double ring) and
   its gold frame brightens; the active row's fill and caret carry the rest. */
.dialogue-choices:focus-visible {
  border-color: rgba(228, 200, 142, 0.72);
  box-shadow:
    var(--shadow-lg),
    0 0 0 1px rgba(228, 200, 142, 0.18),
    0 0 22px -6px var(--gold-glow),
    inset 0 0 0 1px rgba(0, 0, 0, 0.55),
    inset 0 1px 0 1px rgba(238, 221, 180, 0.06);
}

/* The rows scroll inside the card when the stage is too short for them;
   the card's frame and crest stay put. */
.dialogue-choices__rows {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: clamp(8px, 1.3vh, 14px) 10px clamp(6px, 0.93vh, 10px);
  display: flex;
  flex-direction: column;
  gap: clamp(2px, 0.37vh, 4px);
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-width: thin;
}

/* The card's crest: a gold hairline across the top edge with a small
   lozenge at its centre (decorative, like the reference caption card). */
.dialogue-choices::before {
  content: "";
  position: absolute;
  left: 18%;
  right: 18%;
  top: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gold-400), transparent);
  pointer-events: none;
}

.dialogue-choices::after {
  content: "";
  position: absolute;
  left: 50%;
  top: -3px;
  width: 6px;
  height: 6px;
  margin-left: -3px;
  transform: rotate(45deg);
  background: var(--gold-400);
  box-shadow: 0 0 8px var(--gold-glow);
  pointer-events: none;
}

.dialogue-choices__row {
  position: relative;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  box-sizing: border-box;
  /* 44px at the 1080px reference height, 36px at 720px, so the seven rows
     of a four-pick conversation fit the shortest stage unscrolled. */
  min-height: clamp(36px, 4.075vh, 44px);
  padding: 4px 14px 4px 26px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--paper-100);
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}

.dialogue-choices__row:hover {
  background: rgba(231, 224, 209, 0.05);
}

/* The trailing rows (or the exits' back row) open under a hairline. */
.dialogue-choices__row--trailing:not(:first-child) {
  margin-top: 7px;
}

.dialogue-choices__row--trailing:not(:first-child)::after {
  content: "";
  position: absolute;
  left: 12px;
  right: 12px;
  top: -6px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(185, 154, 96, 0.34), transparent);
  pointer-events: none;
}

.dialogue-choices__badge {
  flex: none;
  display: grid;
  place-items: center;
  box-sizing: border-box;
  width: clamp(24px, 2.593vh, 28px);
  height: clamp(24px, 2.593vh, 28px);
  border: 1px solid rgba(185, 154, 96, 0.7);
  border-radius: 6px;
  background: rgba(185, 154, 96, 0.08);
  color: var(--gold-400);
  font: 14px/1 var(--f-mono);
}

/* The glyph badges (↦ ✕, exit arrows) read better in the sans face. */
.dialogue-choices__row:not(.dialogue-choices__row--pick) .dialogue-choices__badge {
  font: 15px/1 var(--f-sans);
}

.dialogue-choices__badge-icon {
  width: 17px;
  height: 17px;
}

.dialogue-choices__text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* A pick is something the player says: the serif reading face. The
   trailing rows are commands, set quieter in the sans face. */
.dialogue-choices__label {
  font-family: var(--f-serif);
  font-size: clamp(17px, 1.852vh, 20px);
  line-height: 1.4;
  color: var(--paper-50);
  overflow-wrap: anywhere;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
}

.dialogue-choices__row:not(.dialogue-choices__row--pick) .dialogue-choices__label {
  font-family: var(--f-sans);
  font-size: clamp(15px, 1.574vh, 17px);
  letter-spacing: 0.04em;
  color: var(--paper-300);
}

.dialogue-choices:focus .dialogue-choices__row--active .dialogue-choices__label {
  color: var(--paper-50);
}

.dialogue-choices__reason {
  font-family: var(--f-sans);
  font-size: 13px;
  line-height: 1.45;
  color: var(--seal-400);
}

.dialogue-choices__row--leave .dialogue-choices__badge {
  border-color: rgba(169, 50, 42, 0.8);
  background: rgba(169, 50, 42, 0.1);
  color: var(--seal-400);
}

.dialogue-choices__row[aria-disabled="true"] {
  cursor: default;
}

.dialogue-choices__row[aria-disabled="true"] .dialogue-choices__label {
  color: var(--paper-500);
}

.dialogue-choices__row[aria-disabled="true"] .dialogue-choices__badge {
  border-style: dashed;
  border-color: var(--ink-600);
  background: transparent;
  color: var(--paper-500);
}

/* The active row (focus shown by shape and fill, never colour alone): the
   dock's muted-gold fill and its leading ▸ caret, while the list holds
   focus. */
.dialogue-choices:focus .dialogue-choices__row--active {
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.3), rgba(185, 154, 96, 0.08));
  border-color: rgba(185, 154, 96, 0.75);
}

.dialogue-choices:focus .dialogue-choices__row--active::before {
  content: "▸";
  position: absolute;
  left: 9px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--gold-400);
  font-size: 13px;
}

.dialogue-choices:focus .dialogue-choices__row--active .dialogue-choices__badge {
  border-color: var(--gold-400);
  background: linear-gradient(180deg, var(--gold-400), var(--gold-500));
  color: var(--ink-950);
}

/* A disabled exit keeps its shape when active: a quiet frame and the
   dashed badge, never the gold fill that promises an action. */
.dialogue-choices:focus .dialogue-choices__row--active[aria-disabled="true"] {
  background: rgba(231, 224, 209, 0.05);
  border-color: var(--ink-600);
}

.dialogue-choices:focus .dialogue-choices__row--active[aria-disabled="true"]::before {
  color: var(--paper-500);
}

.dialogue-choices:focus .dialogue-choices__row--active[aria-disabled="true"] .dialogue-choices__badge {
  border-color: var(--paper-700);
  background: transparent;
  color: var(--paper-400);
}

.dialogue-choices:focus .dialogue-choices__row--active[aria-disabled="true"] .dialogue-choices__label {
  color: var(--paper-300);
}

.dialogue-choices:focus .dialogue-choices__row--leave.dialogue-choices__row--active {
  background: linear-gradient(90deg, rgba(169, 50, 42, 0.32), rgba(169, 50, 42, 0.08));
  border-color: rgba(207, 68, 68, 0.7);
}

.dialogue-choices:focus .dialogue-choices__row--leave.dialogue-choices__row--active::before {
  color: var(--seal-400);
}

.dialogue-choices:focus .dialogue-choices__row--leave.dialogue-choices__row--active .dialogue-choices__badge {
  border-color: var(--seal-500);
  background: var(--seal-600);
  color: var(--paper-50);
}
</style>
