<script setup>
// ChoiceCard (exploration-presence-rail design D1; scene overview redesign
// §4.2): the one centred card shell. Extracted from DialogueChoices, it owns
// the card frame, crest, and corner brackets; the digit-badged rows and the
// hairline rule before the trailing rows; the active row's fill and caret;
// the single-tab-stop keyboard composite; and the staggered entrance with
// its motion-level handling. It is passive: rows arrive as data and an
// activation emits `pick(key)` (an enabled row) or `back` (a back row, or
// Escape). Consumers: the dialogue choice list, the person-focus verb card,
// and the presence overflow card.
//
// One keyboard composite, one tab stop: DOM focus rests on the menu
// container, which names its active row through `aria-activedescendant`.
// ArrowUp / ArrowDown wrap, Home / End jump, Enter / Space activate (a held
// repeat never does), digits 1–N activate the Nth row, and Escape emits
// `back`. Every handled key is consumed before it can bubble to the
// document keyboard bridge. A pointer activation focuses the list and runs
// the same activation path as Enter.
//
// The dialogue list keeps its exact contract through four switches:
// `escapeBack` (Escape passes through outside its exits view), `digitRows`
// and `claimDigits` (only its picks take digits, and other digits pass
// through), and `trapFocus` (Tab passes through). `block` renders a second
// BEM block in parallel with the generic `choice-card*` classes, so the
// dialogue list's elements keep every `dialogue-choices*` class.
//
// The entrance (webclient-mode-transitions D5): the card fades in and each
// row fades and rises into place one stagger step after the one above it.
// Pure CSS keyframes on elements that are in the DOM, focusable, and
// clickable from their first frame. A `viewKey` change renders new rows,
// which stagger in the same way. `entrance` false (a reconnect's frame)
// shows the card at rest.
//
// The initial highlight: the card opens with its first enabled non-back row
// active, shown quietly even while the card does not hold focus.
import { computed, nextTick, onMounted, ref, useId, watch } from "vue";

const props = defineProps({
  // [{key, label, badge, kind, enabled, reason, back, icon, testId,
  //   reasonTestId, keywordId}]
  rows: { type: Array, default: () => [] },
  // Rows re-key (and re-stagger) when this changes.
  viewKey: { type: String, default: "" },
  // The first trailing row: it opens under a hairline rule.
  trailingIndex: { type: Number, default: -1 },
  // A quiet caption above the rows.
  caption: { type: String, default: null },
  ariaLabel: { type: String, default: "選項" },
  testId: { type: String, default: "choice-card" },
  // Whether the card animates in when it mounts. Read once, at mount.
  entrance: { type: Boolean, default: true },
  // Escape is consumed and emits `back`.
  escapeBack: { type: Boolean, default: true },
  // How many leading rows the digits address (null: every non-back row).
  digitRows: { type: Number, default: null },
  // Consume a digit beyond `digitRows` too (it then does nothing).
  claimDigits: { type: Boolean, default: true },
  // Tab and Shift+Tab are consumed: focus stays on the card.
  trapFocus: { type: Boolean, default: false },
  // Take focus when mounted.
  autofocus: { type: Boolean, default: false },
  // A second BEM block rendered in parallel with `choice-card`.
  block: { type: String, default: null },
});

const emit = defineEmits(["pick", "back"]);

const listRef = ref(null);
const scrollRef = ref(null);
const idPrefix = useId();
// The entrance is decided once, at mount; the rows' stillness ends at the
// first view swap, whose new rows stagger in.
const cardStill = !props.entrance;
const rowsStill = ref(!props.entrance);

// Both class blocks for one element suffix ("" is the block itself).
function cls(suffix = "") {
  const generic = `choice-card${suffix}`;
  return props.block ? [generic, `${props.block}${suffix}`] : [generic];
}

function firstEnabled(list) {
  const index = list.findIndex((row) => row.enabled !== false && !row.back);
  return index < 0 ? 0 : index;
}

const activeIndex = ref(firstEnabled(props.rows));

const digitCount = computed(() =>
  props.digitRows === null ? props.rows.filter((row) => !row.back).length : props.digitRows,
);

function rowId(index) {
  return `${idPrefix}-row-${index}`;
}

function reasonId(index) {
  return `${idPrefix}-reason-${index}`;
}

// A committed update that shortens the rows keeps the active row in range.
watch(
  () => props.rows.length,
  (length) => {
    if (activeIndex.value > length - 1) {
      activeIndex.value = Math.max(0, length - 1);
    }
  },
);

watch(
  () => props.viewKey,
  () => {
    rowsStill.value = false;
  },
);

function setActive(index) {
  activeIndex.value = index;
  void nextTick(() => {
    const el = Array.from(scrollRef.value?.children || []).find((child) => child.id === rowId(index));
    el?.scrollIntoView?.({ block: "nearest" });
  });
}

function activate(index) {
  const row = props.rows[index];
  if (!row) {
    return;
  }
  if (row.back) {
    emit("back", row.key);
    return;
  }
  if (row.enabled === false) {
    return;
  }
  emit("pick", row.key);
}

function consume(event) {
  event.preventDefault();
  event.stopPropagation();
}

function onKeydown(event) {
  if (event.ctrlKey || event.altKey || event.metaKey) {
    return;
  }
  const count = props.rows.length;
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
  // Shift+Enter / Shift+Space are not the list's activation keys.
  if ((key === "Enter" || key === " ") && !event.shiftKey) {
    consume(event);
    if (!event.repeat) {
      activate(activeIndex.value);
    }
    return;
  }
  if (key === "Escape") {
    if (props.escapeBack) {
      consume(event);
      emit("back", null);
    }
    return;
  }
  if (key === "Tab") {
    if (props.trapFocus) {
      consume(event);
    }
    return;
  }
  if (key.length === 1 && key >= "1" && key <= "9") {
    const index = Number(key) - 1;
    if (index < digitCount.value) {
      consume(event);
      if (!event.repeat) {
        setActive(index);
        activate(index);
      }
    } else if (props.claimDigits) {
      consume(event);
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

onMounted(() => {
  if (props.autofocus) {
    focus();
  }
});

defineExpose({ focus, setActive });
</script>

<template>
  <div
    ref="listRef"
    :class="[
      cls(),
      {
        'choice-card--still': cardStill,
        'choice-card--rows-still': rowsStill,
        [`${block}--still`]: !!block && cardStill,
        [`${block}--rows-still`]: !!block && rowsStill,
      },
    ]"
    role="menu"
    :aria-label="ariaLabel"
    tabindex="0"
    :data-testid="testId"
    :data-view="viewKey || null"
    :aria-activedescendant="rows.length ? rowId(activeIndex) : null"
    @keydown="onKeydown"
  >
    <span :class="cls('__corners')" aria-hidden="true"></span>
    <div v-if="caption" :class="cls('__caption')" aria-hidden="true">{{ caption }}</div>
    <div :key="viewKey" ref="scrollRef" :class="cls('__rows')" :style="{ '--row-count': rows.length }">
    <div
      v-for="(row, index) in rows"
      :id="rowId(index)"
      :key="`${viewKey}-${row.key}`"
      :class="[
        cls('__row'),
        cls(`__row--${row.kind || 'row'}`),
        index === activeIndex ? cls('__row--active') : [],
        index === trailingIndex ? cls('__row--trailing') : [],
      ]"
      role="menuitem"
      :data-testid="row.testId || 'choice-card-row'"
      :data-row-key="row.key"
      :data-keyword-id="row.keywordId"
      :data-active="index === activeIndex ? 'true' : 'false'"
      :style="{ '--row-index': index }"
      :aria-disabled="row.enabled === false ? 'true' : null"
      :aria-describedby="row.reason ? reasonId(index) : null"
      @click="onRowClick(index)"
    >
      <span :class="cls('__badge')" aria-hidden="true" :data-badge="row.badge">
        <!-- The keyboard glyph draws tiny in the loaded text faces, so a
             keyboard badge is drawn as a small keyboard. -->
        <svg
          v-if="row.icon === 'keyboard'"
          :class="cls('__badge-icon')"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
        >
          <rect x="2.5" y="6" width="19" height="12" rx="2.2" />
          <path d="M6.5 10h.01M10 10h.01M14 10h.01M17.5 10h.01M8 14h8" stroke-width="2" />
        </svg>
        <!-- A close badge's ✕ is drawn too: two fine strokes, where the text
             glyph read as a heavy Latin X. -->
        <svg
          v-else-if="row.icon === 'close'"
          :class="[cls('__badge-icon'), cls('__badge-icon--close'), row.kind === 'leave' ? cls('__badge-icon--leave') : []]"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
        >
          <path d="M7 7l10 10M17 7L7 17" />
        </svg>
        <template v-else>{{ row.badge }}</template>
      </span>
      <span :class="cls('__text')">
        <span :class="cls('__label')">{{ row.label }}</span>
        <span
          v-if="row.reason"
          :id="reasonId(index)"
          :class="cls('__reason')"
          :data-testid="row.reasonTestId || 'choice-card-reason'"
        >{{ row.reason }}</span>
      </span>
    </div>
    </div>
  </div>
</template>

<style>
/* The choice card (webclient-dialogue-choices-overlay D6): the reference's
   caption-panel treatment. */
.choice-card {
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
  backdrop-filter: blur(calc(6px * var(--ui-scale)));
  outline: none;
  pointer-events: auto;
}

/* The entrance (webclient-mode-transitions D5). The card surfaces first;
   the rows follow one stagger step apart, each fading up as it rises the
   small shift into place on a decelerating curve. `backwards` holds a row at
   its starting pose through its delay; after the animation nothing is
   filled, so hover, focus, and the active row's styles are untouched. The
   reduced level keeps the fades (stagger and rise are 0); the off level
   resolves every duration and delay to 0. */
.choice-card {
  animation: elosern-choice-card-in var(--motion-reveal) var(--ease-standard) backwards;
}
.choice-card__row {
  animation: elosern-choice-row-in var(--motion-reveal) var(--ease-enter)
    calc(var(--motion-stagger) * var(--row-index, 0)) backwards;
}
/* While the rows rise, the last ones sit a shift below their rest, which a
   tight stage (1280x720) would turn into a scrollbar flashing on and off;
   the scroller clips instead for exactly the entrance's length. */
.choice-card__rows {
  animation: elosern-choice-rows-clip
    calc(var(--motion-stagger) * var(--row-count, 1) + var(--motion-reveal)) linear;
}
.choice-card--still,
.choice-card--rows-still .choice-card__rows,
.choice-card--rows-still .choice-card__row {
  animation: none;
}
.choice-card__caption {
  animation: elosern-choice-card-in var(--motion-reveal) var(--ease-standard) backwards;
}

@keyframes elosern-choice-rows-clip {
  from,
  to {
    overflow-y: hidden;
  }
}

@keyframes elosern-choice-card-in {
  from {
    opacity: 0;
  }
}

@keyframes elosern-choice-row-in {
  from {
    opacity: 0;
    transform: translateY(calc(var(--motion-shift-sm) * var(--motion-travel)));
  }
}

/* The quiet caption: it names what the rows are. */
.choice-card__caption {
  flex: none;
  padding: calc(12px * var(--ui-scale)) calc(20px * var(--ui-scale)) 0;
  font: var(--text-xs)/1.4 var(--f-sans);
  letter-spacing: 0.3em;
  color: var(--gold-500);
  text-align: center;
}

.choice-card__caption + .choice-card__rows {
  padding-top: calc(8px * var(--ui-scale));
}

/* Keyboard focus on the one tab stop: the card keeps its drop shadow (the
   global `:focus-visible` ring would replace it with a hard double ring) and
   its gold frame brightens; the active row's fill and caret carry the rest. */
.choice-card:focus-visible {
  border-color: rgba(228, 200, 142, 0.72);
  box-shadow:
    var(--shadow-lg),
    0 0 0 1px rgba(228, 200, 142, 0.18),
    0 0 calc(22px * var(--ui-scale)) calc(-6px * var(--ui-scale)) var(--gold-glow),
    inset 0 0 0 1px rgba(0, 0, 0, 0.55),
    inset 0 1px 0 1px rgba(238, 221, 180, 0.06);
}

/* The rows scroll inside the card when the stage is too short for them;
   the card's frame and crest stay put. */
.choice-card__rows {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: clamp(8px * var(--ui-scale), 1.3vh, 14px * var(--ui-scale)) calc(10px * var(--ui-scale)) clamp(6px * var(--ui-scale), 0.93vh, 10px * var(--ui-scale));
  display: flex;
  flex-direction: column;
  gap: clamp(2px, 0.37vh, 4px * var(--ui-scale));
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-width: thin;
}

/* The card's crest: a gold hairline across the top edge with a small
   lozenge at its centre (decorative, like the reference caption card). */
.choice-card::before {
  content: "";
  position: absolute;
  left: 18%;
  right: 18%;
  top: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gold-400), transparent);
  pointer-events: none;
}

.choice-card::after {
  content: "";
  position: absolute;
  left: 50%;
  top: calc(-3px * var(--ui-scale));
  width: calc(6px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  margin-left: calc(-3px * var(--ui-scale));
  transform: rotate(45deg);
  background: var(--gold-400);
  box-shadow: 0 0 calc(8px * var(--ui-scale)) var(--gold-glow);
  pointer-events: none;
}

/* The card's corner ornaments (webclient-message-typesetting): four small
   gold brackets just inside the frame, at rest strength. They brighten with
   the frame while the card holds keyboard focus. Decorative and
   pointer-inert. */
.choice-card__corners {
  position: absolute;
  inset: calc(3px * var(--ui-scale));
  z-index: 1;
  pointer-events: none;
  opacity: 0.55;
  --corner: rgba(185, 154, 96, 0.9);
  background:
    linear-gradient(var(--corner), var(--corner)) top left / calc(8px * var(--ui-scale)) 1px no-repeat,
    linear-gradient(var(--corner), var(--corner)) top left / 1px calc(8px * var(--ui-scale)) no-repeat,
    linear-gradient(var(--corner), var(--corner)) top right / calc(8px * var(--ui-scale)) 1px no-repeat,
    linear-gradient(var(--corner), var(--corner)) top right / 1px calc(8px * var(--ui-scale)) no-repeat,
    linear-gradient(var(--corner), var(--corner)) bottom left / calc(8px * var(--ui-scale)) 1px no-repeat,
    linear-gradient(var(--corner), var(--corner)) bottom left / 1px calc(8px * var(--ui-scale)) no-repeat,
    linear-gradient(var(--corner), var(--corner)) bottom right / calc(8px * var(--ui-scale)) 1px no-repeat,
    linear-gradient(var(--corner), var(--corner)) bottom right / 1px calc(8px * var(--ui-scale)) no-repeat;
  transition: opacity var(--motion-fast) var(--ease-standard);
}

.choice-card:focus-visible .choice-card__corners {
  opacity: 1;
}

.choice-card__row {
  position: relative;
  flex: none;
  display: flex;
  align-items: center;
  gap: calc(14px * var(--ui-scale));
  box-sizing: border-box;
  /* 36px at the 1451x790 reference height and below, growing to 44px on a
     taller stage, so the seven rows of a four-pick conversation fit the
     reference stage unscrolled. */
  min-height: clamp(36px * var(--ui-scale), 4.075vh, 44px * var(--ui-scale));
  padding: calc(4px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(4px * var(--ui-scale)) calc(26px * var(--ui-scale));
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--paper-100);
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}

.choice-card__row:hover {
  background: rgba(231, 224, 209, 0.05);
}

/* The trailing rows (or a back row) open under a hairline. */
.choice-card__row--trailing:not(:first-child) {
  margin-top: calc(7px * var(--ui-scale));
}

.choice-card__row--trailing:not(:first-child)::after {
  content: "";
  position: absolute;
  left: calc(12px * var(--ui-scale));
  right: calc(12px * var(--ui-scale));
  top: calc(-6px * var(--ui-scale));
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(185, 154, 96, 0.34), transparent);
  pointer-events: none;
}

.choice-card__badge {
  flex: none;
  display: grid;
  place-items: center;
  box-sizing: border-box;
  width: clamp(24px * var(--ui-scale), 2.593vh, 28px * var(--ui-scale));
  height: clamp(24px * var(--ui-scale), 2.593vh, 28px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.7);
  border-radius: var(--radius);
  background: rgba(185, 154, 96, 0.08);
  color: var(--gold-400);
  font: var(--text-md)/1 var(--f-mono);
}

/* The glyph badges (↦ ✕, exit arrows) read better in the sans face. */
.choice-card__row:not(.choice-card__row--pick):not(.choice-card__row--verb) .choice-card__badge {
  font: var(--text-base)/1 var(--f-sans);
}

.choice-card__badge-icon {
  width: calc(17px * var(--ui-scale));
  height: calc(17px * var(--ui-scale));
}

.choice-card__text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* A pick is something the player says: the serif reading face. The
   trailing rows are commands, set quieter in the sans face. */
.choice-card__label {
  font-family: var(--f-serif);
  font-size: clamp(17px * var(--ui-scale), 1.852vh, 20px * var(--ui-scale));
  line-height: 1.4;
  color: var(--paper-50);
  overflow-wrap: anywhere;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
}

.choice-card__row:not(.choice-card__row--pick) .choice-card__label {
  font-family: var(--f-sans);
  /* The command rows' lower bound is the shared 16px floor
     (retarget-desktop-viewport-contract D4). */
  font-size: clamp(16px * var(--ui-scale), 1.574vh, 17px * var(--ui-scale));
  letter-spacing: 0.04em;
  color: var(--paper-300);
}

/* A verb on the person-focus card is the card's main choice: it reads as
   brightly as a dialogue pick, in the command face. */
.choice-card__row--verb .choice-card__label {
  color: var(--paper-100);
}

.choice-card:focus .choice-card__row--active .choice-card__label {
  color: var(--paper-50);
}

.choice-card__reason {
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  line-height: 1.45;
  color: var(--seal-400);
}

/* Leaving is marked on its icon only (webclient-message-typesetting): a
   seal-tinted badge and cross, never a red frame around the whole row. */
.choice-card__row--leave .choice-card__badge {
  border-color: rgba(169, 50, 42, 0.8);
  background: rgba(169, 50, 42, 0.1);
  color: var(--seal-400);
}

.choice-card__badge-icon--close {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}

.choice-card__row[aria-disabled="true"] {
  cursor: default;
}

.choice-card__row[aria-disabled="true"] .choice-card__label {
  color: var(--paper-500);
}

.choice-card__row[aria-disabled="true"] .choice-card__badge {
  border-style: dashed;
  border-color: var(--ink-600);
  background: transparent;
  color: var(--paper-500);
}

/* The initial highlight while the card does not hold focus
   (webclient-message-typesetting): the active row carries a quiet version
   of the focused treatment — a faint fill, a hairline frame, and a dim
   caret — so it reads as where the keys will start, not as a choice made. */
.choice-card:not(:focus) .choice-card__row--active:not([aria-disabled="true"]) {
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.12), rgba(185, 154, 96, 0.02));
  border-color: rgba(185, 154, 96, 0.32);
}

.choice-card:not(:focus) .choice-card__row--active::before {
  content: "▸";
  position: absolute;
  left: calc(9px * var(--ui-scale));
  top: 50%;
  transform: translateY(-50%);
  color: var(--gold-500);
  font-size: var(--text-sm);
  opacity: 0.7;
}

.choice-card:not(:focus) .choice-card__row--active[aria-disabled="true"]::before {
  color: var(--paper-500);
}

/* The active row (focus shown by shape and fill, never colour alone): the
   dock's muted-gold fill and its leading ▸ caret, while the card holds
   focus. */
.choice-card:focus .choice-card__row--active {
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.3), rgba(185, 154, 96, 0.08));
  border-color: rgba(185, 154, 96, 0.75);
}

.choice-card:focus .choice-card__row--active::before {
  content: "▸";
  position: absolute;
  left: calc(9px * var(--ui-scale));
  top: 50%;
  transform: translateY(-50%);
  color: var(--gold-400);
  font-size: var(--text-sm);
}

.choice-card:focus .choice-card__row--active .choice-card__badge {
  border-color: var(--gold-400);
  background: linear-gradient(180deg, var(--gold-400), var(--gold-500));
  color: var(--ink-950);
}

/* A disabled row keeps its shape when active: a quiet frame and the
   dashed badge, never the gold fill that promises an action. */
.choice-card:focus .choice-card__row--active[aria-disabled="true"] {
  background: rgba(231, 224, 209, 0.05);
  border-color: var(--ink-600);
}

.choice-card:focus .choice-card__row--active[aria-disabled="true"]::before {
  color: var(--paper-500);
}

.choice-card:focus .choice-card__row--active[aria-disabled="true"] .choice-card__badge {
  border-color: var(--paper-700);
  background: transparent;
  color: var(--paper-400);
}

.choice-card:focus .choice-card__row--active[aria-disabled="true"] .choice-card__label {
  color: var(--paper-300);
}

.choice-card:focus .choice-card__row--leave.choice-card__row--active .choice-card__badge {
  border-color: var(--seal-500);
  background: var(--seal-600);
  color: var(--paper-50);
}
</style>
