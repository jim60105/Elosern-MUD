<script setup>
// TimeChoiceCard (redesign-rest-entry design D4; rest entry redesign §3): the
// rest entry's first layer, opened by the place card's 休息. Two large choice
// tiles inside the shared `choice-card` frame — 1 等待 (stay awake) and
// 2 睡眠 (sleep) — each with a line icon, a hint, and one context line the
// client already holds (`現在 HH:MM`, `精力 N%（stage label）`), plus a corner
// ✕. It holds no inputs and adds no action id: it is presentational and
// emits only `pick("wait" | "sleep")` and `close`.
//
// Keys (handled on the root, each consumed before it can reach the document
// keyboard bridge): 1 / 2 pick a tile (ignored while locked), ← → ↑ ↓ move
// focus between the tiles with wrap, Home / End jump, Escape closes, and Tab
// cycles over the tiles and the ✕. Enter / Space activate the focused button
// natively, so they are the only keys left to bubble (as in QuestionCard).
//
// Locked (a mutation in flight or awaiting its revision, or the session not
// live): both tiles carry `aria-disabled="true"`, stay focusable, and are
// described by the one `role="status"` reason; digits and clicks pick
// nothing.
//
// The narrow layout is measured, not queried (`var()` is not allowed in a
// media or container condition): the parent's width below
// `320px * --ui-scale` stacks the tiles, kept current by a ResizeObserver.
import { computed, onBeforeUnmount, onMounted, ref, useId } from "vue";
import { focusableElements } from "./focus-trap.js";

const TIME_CHOICE_LOCKED_REASON = "上一個行動尚未完成，請稍候。";

const props = defineProps({
  // The clock part of the committed world-time label (`HH:MM`), or null.
  timeLabel: { type: String, default: null },
  // The controlled body's fatigue row (`{reserve_percent, label}`), or null.
  fatigue: { type: Object, default: null },
  locked: { type: Boolean, default: false },
  // Whether the card animates in when it mounts. Read once, at mount.
  entrance: { type: Boolean, default: true },
  // Take focus when mounted, on `initialTile`.
  autofocus: { type: Boolean, default: true },
  initialTile: { type: String, default: "wait" },
});

const emit = defineEmits(["pick", "close"]);

const idPrefix = useId();
const headingId = `${idPrefix}-heading`;
const statusId = `${idPrefix}-locked`;
const rootRef = ref(null);
const tileRefs = {};
const stacked = ref(false);
const cardStill = !props.entrance;
let observer = null;

const TILE_KEYS = ["wait", "sleep"];

const tiles = computed(() => [
  {
    key: "wait",
    badge: "1",
    label: "等待",
    hint: "保持清醒，讓時間流逝",
    context: typeof props.timeLabel === "string" && props.timeLabel !== "" ? { lead: `現在 ${props.timeLabel}` } : null,
  },
  {
    key: "sleep",
    badge: "2",
    label: "睡眠",
    hint: "入睡，恢復精力",
    context: props.fatigue
      ? { lead: `精力 ${props.fatigue.reserve_percent}%`, stage: `（${props.fatigue.label}）` }
      : null,
  },
]);

function hintId(key) {
  return `${idPrefix}-${key}-hint`;
}

function contextId(key) {
  return `${idPrefix}-${key}-context`;
}

function describedBy(tile) {
  return [hintId(tile.key), tile.context ? contextId(tile.key) : null, props.locked ? statusId : null]
    .filter(Boolean)
    .join(" ");
}

function setTileRef(key, el) {
  tileRefs[key] = el;
}

function focusTile(key) {
  const el = tileRefs[key];
  el?.focus({ preventScroll: true });
}

function pick(key) {
  if (props.locked) {
    return;
  }
  emit("pick", key);
}

function focusedTileIndex() {
  const active = typeof document === "undefined" ? null : document.activeElement;
  const key = active && active.getAttribute ? active.getAttribute("data-tile") : null;
  return TILE_KEYS.indexOf(key);
}

function consume(event) {
  event.preventDefault();
  event.stopPropagation();
}

function onKeyDown(event) {
  if (event.ctrlKey || event.altKey || event.metaKey) {
    return;
  }
  const key = event.key;
  if (key === "1" || key === "2") {
    consume(event);
    if (!event.repeat) {
      pick(TILE_KEYS[Number(key) - 1]);
    }
    return;
  }
  if (key === "ArrowRight" || key === "ArrowDown" || key === "ArrowLeft" || key === "ArrowUp") {
    consume(event);
    const step = key === "ArrowRight" || key === "ArrowDown" ? 1 : -1;
    const current = focusedTileIndex();
    const from = current < 0 ? (step > 0 ? -1 : 0) : current;
    focusTile(TILE_KEYS[(from + step + TILE_KEYS.length) % TILE_KEYS.length]);
    return;
  }
  if (key === "Home" || key === "End") {
    consume(event);
    focusTile(key === "Home" ? TILE_KEYS[0] : TILE_KEYS[TILE_KEYS.length - 1]);
    return;
  }
  if (key === "Escape") {
    consume(event);
    emit("close");
    return;
  }
  if (key === "Tab") {
    consume(event);
    const list = focusableElements(rootRef.value);
    if (list.length === 0) {
      return;
    }
    const index = list.indexOf(document.activeElement);
    const step = event.shiftKey ? -1 : 1;
    const next = index < 0 ? (event.shiftKey ? list.length - 1 : 0) : (index + step + list.length) % list.length;
    list[next].focus({ preventScroll: true });
    return;
  }
  // Enter / Space reach the focused button natively; every other key stays
  // inside the card.
  if (key !== "Enter" && key !== " ") {
    event.stopPropagation();
  }
}

function uiScale() {
  if (typeof getComputedStyle !== "function" || typeof document === "undefined") {
    return 1;
  }
  const value = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--ui-scale"));
  return Number.isFinite(value) && value > 0 ? value : 1;
}

function measure() {
  const parent = rootRef.value?.parentElement;
  const width = parent ? parent.clientWidth : 0;
  // An unmeasured parent (zero width: not laid out yet) keeps the default
  // side-by-side tiles.
  stacked.value = width > 0 && width < 320 * uiScale();
}

onMounted(() => {
  measure();
  const parent = rootRef.value?.parentElement;
  if (parent && typeof ResizeObserver !== "undefined") {
    observer = new ResizeObserver(() => measure());
    observer.observe(parent);
  }
  if (props.autofocus) {
    focusTile(TILE_KEYS.includes(props.initialTile) ? props.initialTile : "wait");
  }
});

onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
});

defineExpose({ focusTile });
</script>

<template>
  <section
    ref="rootRef"
    class="choice-card time-choice"
    :class="{ 'choice-card--still': cardStill, 'time-choice--stacked': stacked }"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="headingId"
    data-testid="wait-card"
    data-card-kind="wait"
    @keydown="onKeyDown"
  >
    <span class="choice-card__corners" aria-hidden="true"></span>
    <h2 :id="headingId" class="visually-hidden">等待或睡眠</h2>
    <div class="choice-card__caption" aria-hidden="true">度過時間</div>
    <div class="time-choice__tiles">
      <button
        v-for="tile in tiles"
        :key="tile.key"
        :ref="(el) => setTileRef(tile.key, el)"
        type="button"
        class="time-choice__tile"
        :class="`time-choice__tile--${tile.key}`"
        data-testid="wait-card-tile"
        :data-tile="tile.key"
        :aria-disabled="locked ? 'true' : null"
        :aria-describedby="describedBy(tile)"
        @click="pick(tile.key)"
      >
        <span class="time-choice__badge" aria-hidden="true">{{ tile.badge }}</span>
        <svg
          v-if="tile.key === 'wait'"
          class="time-choice__icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
        <svg
          v-else
          class="time-choice__icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M20 14.5a8 8 0 0 1-10.5-10.5 8 8 0 1 0 10.5 10.5z" />
          <path d="M16 3.5v3M14.5 5h3" />
        </svg>
        <span class="time-choice__label">{{ tile.label }}</span>
        <span class="time-choice__text">
          <span :id="hintId(tile.key)" class="time-choice__hint">{{ tile.hint }}</span>
          <span
            v-if="tile.context"
            :id="contextId(tile.key)"
            class="time-choice__context"
            data-testid="wait-card-tile-context"
          ><span class="time-choice__numerals">{{ tile.context.lead }}</span><span
            v-if="tile.context.stage"
            class="time-choice__stage"
          >{{ tile.context.stage }}</span></span>
        </span>
      </button>
    </div>
    <p v-if="locked" :id="statusId" role="status" class="time-choice__locked">{{ TIME_CHOICE_LOCKED_REASON }}</p>
    <button
      type="button"
      class="time-choice__close"
      aria-label="關閉並回到探索"
      title="關閉"
      data-testid="wait-card-close"
      @click="emit('close')"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
        <path d="M7 7l10 10M17 7L7 17" />
      </svg>
    </button>
  </section>
</template>

<style scoped>
/* The first layer (rest entry redesign §3, after TimeChoicePrototype.vue):
   the shared `choice-card` frame (its fill, crest, corners, caption, and
   entrance are ChoiceCard's unscoped rules), centred in the flex-column
   `choices` anchor. */
.time-choice {
  align-self: center;
  width: min(100%, calc(460px * var(--ui-scale)));
  padding: 0 calc(14px * var(--ui-scale)) calc(14px * var(--ui-scale));
  gap: calc(10px * var(--ui-scale));
}
.time-choice__tiles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: calc(10px * var(--ui-scale));
}
.time-choice--stacked .time-choice__tiles {
  grid-template-columns: 1fr;
}
.time-choice__tile {
  position: relative;
  display: grid;
  grid-template-rows: auto auto 1fr;
  justify-items: center;
  gap: calc(6px * var(--ui-scale));
  min-height: calc(132px * var(--ui-scale));
  padding: calc(16px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(12px * var(--ui-scale));
  color: var(--paper-100);
  font: inherit;
  text-align: center;
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.08), rgba(185, 154, 96, 0.02));
  border: 1px solid rgba(185, 154, 96, 0.35);
  border-radius: var(--radius);
  cursor: pointer;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    background var(--motion-fast) var(--ease-standard);
}
.time-choice--stacked .time-choice__tile {
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  justify-items: start;
  align-items: center;
  column-gap: calc(12px * var(--ui-scale));
  min-height: calc(76px * var(--ui-scale));
  padding-right: calc(44px * var(--ui-scale));
  text-align: left;
}
.time-choice--stacked .time-choice__icon {
  grid-row: 1 / 3;
}
.time-choice__tile:hover,
.time-choice__tile:focus-visible {
  border-color: var(--gold-500);
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.28), rgba(185, 154, 96, 0.08));
  outline: none;
}
.time-choice__tile:focus-visible {
  box-shadow: 0 0 0 2px var(--gold-400);
}
.time-choice__badge {
  position: absolute;
  top: calc(8px * var(--ui-scale));
  left: calc(8px * var(--ui-scale));
  display: grid;
  place-items: center;
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.7);
  border-radius: var(--radius);
  background: rgba(185, 154, 96, 0.08);
  color: var(--gold-400);
  font: var(--text-sm)/1 var(--f-mono);
}
/* The focused tile's badge takes the active ChoiceCard badge's solid gold. */
.time-choice__tile:focus-visible .time-choice__badge {
  border-color: var(--gold-400);
  background: linear-gradient(180deg, var(--gold-400), var(--gold-500));
  color: var(--ink-950);
}
.time-choice--stacked .time-choice__badge {
  top: 50%;
  left: auto;
  right: calc(10px * var(--ui-scale));
  transform: translateY(-50%);
}
.time-choice__icon {
  width: calc(30px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  color: var(--gold-400);
}
.time-choice__label {
  font: var(--text-xl)/1.2 var(--f-sans);
  letter-spacing: 0.2em;
  color: var(--paper-50);
}
.time-choice__text {
  display: grid;
  gap: calc(6px * var(--ui-scale));
  align-content: start;
}
.time-choice__hint {
  font: var(--text-sm)/1.5 var(--f-sans);
  color: var(--paper-300);
}
/* One line, never split: the numerals keep the mono face, the stage label
   reads in the sans face so the line fits the tile. */
.time-choice__context {
  padding-top: calc(6px * var(--ui-scale));
  border-top: 1px solid rgba(185, 154, 96, 0.2);
  font: var(--text-xs)/1.4 var(--f-mono);
  color: var(--gold-400);
  white-space: nowrap;
}
.time-choice__stage {
  font-family: var(--f-sans);
}
.time-choice--stacked .time-choice__context {
  padding-top: 0;
  border-top: 0;
}
.time-choice__tile[aria-disabled="true"] {
  cursor: not-allowed;
  border-style: dashed;
  border-color: rgba(185, 154, 96, 0.3);
  background: transparent;
}
.time-choice__tile[aria-disabled="true"] .time-choice__icon,
.time-choice__tile[aria-disabled="true"] .time-choice__label {
  color: var(--paper-400);
}
.time-choice__tile[aria-disabled="true"] .time-choice__badge {
  border-style: dashed;
  background: transparent;
  color: var(--paper-400);
}
.time-choice__locked {
  margin: 0;
  font: var(--text-sm)/1.4 var(--f-sans);
  color: var(--paper-400);
  text-align: center;
}
/* The corner ✕ (QuestionCard's `.question-card__close`). */
.time-choice__close {
  position: absolute;
  top: calc(8px * var(--ui-scale));
  right: calc(8px * var(--ui-scale));
  z-index: 2;
  display: grid;
  place-items: center;
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--paper-400);
  cursor: pointer;
}
.time-choice__close svg {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}
.time-choice__close:hover,
.time-choice__close:focus-visible {
  border-color: var(--gold-500);
  color: var(--paper-50);
  outline: none;
}
/* The dialog's accessible name (AvatarArtwork's visually-hidden rule). */
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>
