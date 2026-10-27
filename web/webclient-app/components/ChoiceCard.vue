<script setup>
// ChoiceCard (exploration-presence-rail design D1; scene overview redesign
// §4.2): the one centred card shell. Extracted from DialogueChoices, it owns
// the card frame, crest, and corner brackets; the digit-badged rows and the
// hairline rule before the trailing rows; the active row's fill and caret;
// the single-tab-stop keyboard composite; and the staggered entrance with
// its motion-level handling. It is passive: rows arrive as data and an
// activation emits `pick(key)` (an enabled row) or `back` (a back row, or
// Escape). Consumers: the dialogue choice list, the person-focus verb card,
// the presence overflow card, and the suggestions room card
// (exploration-room-actions), whose rows may carry a second `hint` line and
// whose muted `notes` (the generating, degraded, and empty states) are lines
// above the rows that are not rows at all.
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
// active, shown quietly even while the card does not hold focus. A committed
// update that re-renders the rows keeps the active row by its key while that
// key survives, else keeps its position in range.
//
// Locked rows (authored-dialogue-locked-ui): a row may carry `lock` (a
// visibly locked dialogue topic) and `tip` (the server's canonical
// requirement hint). The two states the card distinguishes:
// - a LOCKED row is selectable. It draws a padlock and carries the text
//   （尚未解鎖） in its accessible name, it never takes `aria-disabled`, and
//   Enter, Space, its digit and a click activate it like any enabled row
//   (its consumer dispatches the row's server payload, and the server plays
//   the authored refusal);
// - a DISABLED row (`enabled: false`, an operational state such as a closed
//   exit) takes `aria-disabled`, keeps its committed reason, and emits
//   nothing.
// A non-empty `tip` is wired to the row through `aria-describedby` (a
// visually hidden copy outside the menu items, so it is a description and
// never part of the name) and is shown in one visual tooltip beside the
// card: the row the pointer rests on wins, else the active row while the
// card holds keyboard focus. The tooltip is not focusable and adds no tab
// stop; it is a descendant of the card, so the pointer can move onto it
// without closing it, and Escape dismisses it (a keyboard-shown tip
// consumes that Escape; a pointer-shown one lets Escape keep its meaning).
// An empty hint renders no tooltip and no description at all.
//
// Unread rows (authored-dialogue-unread-notices): a row may carry `unread`
// (an open formal topic the owner has not read yet, straight from the
// server's choice row). It draws a small gold diamond pip in the row's
// trailing status slot — the slot the padlock uses, so the two never stack
// and a locked row keeps only its lock — lifts its label a step brighter,
// and names the state in text (（未讀）) for assistive technology. The pip
// glows once as the card enters and then rests; it never pulses, so a list
// of new topics does not compete with the scene for attention.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";

const props = defineProps({
  // [{key, label, hint, badge, kind, enabled, reason, back, icon, testId,
  //   reasonTestId, keywordId}]
  rows: { type: Array, default: () => [] },
  // The interaction mapping these rows were rendered from (slice U): a
  // consumer that owns a stable entry mapping publishes its token here, and
  // the DOM copy is what an activation reads back, so an activation can never
  // name a mapping the player did not see.
  mappingToken: { type: String, default: null },
  // Muted lines above the rows; never selectable, never a digit.
  notes: { type: Array, default: () => [] },
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
const tipRef = ref(null);
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

// The rows' contiguous groups (slice U): a run of rows sharing a `group`
// identity draws one real labelled group (`role="group"` with a heading it
// references) inside the composite. A card whose rows carry no group renders
// one unlabelled wrapper, so every other consumer's semantics are unchanged.
// The heading is not a row: it is never focusable, never a menuitem, takes no
// digit and never moves the roving index.
const groupedRows = computed(() => {
  const groups = [];
  props.rows.forEach((row, index) => {
    const id = row.group || "";
    const last = groups[groups.length - 1];
    if (last && last.id === id) {
      last.rows.push({ row, index });
      return;
    }
    groups.push({ id, label: row.groupLabel || null, rows: [{ row, index }] });
  });
  return groups;
});

function rowId(index) {
  return `${idPrefix}-row-${index}`;
}

function groupHeadingId(group) {
  return `${idPrefix}-group-${group.id}`;
}

function reasonId(index) {
  return `${idPrefix}-reason-${index}`;
}

function tipId(index) {
  return `${idPrefix}-tip-${index}`;
}

function describedBy(row, index) {
  const ids = [];
  if (row.reason) {
    ids.push(reasonId(index));
  }
  if (row.tip) {
    ids.push(tipId(index));
  }
  return ids.length ? ids.join(" ") : null;
}

// The tooltip's two sources: the row the pointer rests on (by key, so a
// refresh that removes or moves it never shows another row's hint) and the
// active row while the card holds focus.
const hoverKey = ref(null);
const cardFocused = ref(false);
// The tip Escape dismissed, until its target changes.
const tipDismissed = ref(null);
const tipPlace = ref({ top: 0, side: "right", room: null, placed: false });

const tipTarget = computed(() => {
  if (hoverKey.value !== null) {
    const index = props.rows.findIndex((row) => row.key === hoverKey.value);
    if (index >= 0 && props.rows[index].tip) {
      return { index, source: "pointer", id: `pointer|${props.rows[index].key}` };
    }
  }
  const active = props.rows[activeIndex.value];
  if (cardFocused.value && active && active.tip) {
    return { index: activeIndex.value, source: "focus", id: `focus|${active.key}` };
  }
  return null;
});

const tipShown = computed(() => {
  const target = tipTarget.value;
  if (!target || tipDismissed.value === target.id) {
    return null;
  }
  return { ...target, text: props.rows[target.index].tip };
});

watch(
  () => tipTarget.value?.id ?? null,
  (id) => {
    if (id !== tipDismissed.value) {
      tipDismissed.value = null;
    }
  },
);

// Beside the card, top-aligned with its row (clamped into the scroller's
// visible span and the card's height); it takes the side with room (right
// first) and never grows past the room that side has. Each placement first
// measures the tip at its natural width (no stale room from a previous
// placement), and the tip stays invisible until its first placement lands,
// so it never shows a frame at a provisional position.
const TIP_MARGIN = 8;
let placing = 0;
async function placeTip() {
  const ticket = ++placing;
  if (!tipShown.value || !listRef.value) {
    return;
  }
  tipPlace.value = { ...tipPlace.value, room: null };
  await nextTick();
  const shown = tipShown.value;
  const card = listRef.value;
  if (ticket !== placing || !shown || !card) {
    return;
  }
  const cardBox = card.getBoundingClientRect();
  const viewport = window.innerWidth || document.documentElement.clientWidth || 0;
  const desired = tipRef.value ? tipRef.value.offsetWidth : 0;
  const roomRight = viewport - cardBox.right - TIP_MARGIN * 3;
  const roomLeft = cardBox.left - TIP_MARGIN * 3;
  const side = roomRight >= desired || roomRight >= roomLeft ? "right" : "left";
  const room = viewport ? Math.max(0, Math.floor(side === "right" ? roomRight : roomLeft)) : null;
  tipPlace.value = { ...tipPlace.value, side, room };
  await nextTick();
  if (ticket !== placing || !tipShown.value) {
    return;
  }
  // The tip is positioned from the card's padding box.
  const originTop = cardBox.top + (card.clientTop || 0);
  const rowEl = document.getElementById(rowId(shown.index));
  let rowTop = rowEl ? rowEl.getBoundingClientRect().top - originTop : 0;
  const scroller = scrollRef.value;
  if (scroller) {
    const span = scroller.getBoundingClientRect();
    rowTop = Math.max(span.top - originTop, Math.min(rowTop, span.bottom - originTop));
  }
  const tipHeight = tipRef.value ? tipRef.value.offsetHeight : 0;
  const top = Math.max(0, Math.min(rowTop, card.clientHeight - tipHeight));
  tipPlace.value = { side, room, top: Math.round(top), placed: true };
}

watch(
  () => (tipShown.value ? `${tipShown.value.id}|${tipShown.value.index}|${tipShown.value.text}` : null),
  (shown) => {
    if (shown !== null) {
      tipPlace.value = { ...tipPlace.value, placed: false };
      void placeTip();
    }
  },
  { flush: "post" },
);

// A viewport resize (or a ui-scale change that follows it) re-places an
// open tip; the listener lives only while a tip is shown.
function onWindowResize() {
  void placeTip();
}
watch(
  () => !!tipShown.value,
  (open) => {
    if (open) {
      window.addEventListener("resize", onWindowResize);
    } else {
      window.removeEventListener("resize", onWindowResize);
    }
  },
);
onBeforeUnmount(() => window.removeEventListener("resize", onWindowResize));

// A scroll of the rows, or the end of a row's entrance rise (a tip opened
// while the rows still travel), places the tip on its row again.
function onRowsScroll() {
  if (tipShown.value) {
    void placeTip();
  }
}

// A committed update keeps the active row by key while it survives, and
// otherwise keeps the active position in range.
watch(
  () => props.rows.map((row) => row.key),
  (keys, previous) => {
    const activeKey = previous ? previous[activeIndex.value] : undefined;
    const survivor = activeKey === undefined ? -1 : keys.indexOf(activeKey);
    if (survivor >= 0) {
      activeIndex.value = survivor;
    } else if (activeIndex.value > keys.length - 1) {
      activeIndex.value = Math.max(0, keys.length - 1);
    }
    if (hoverKey.value !== null && !keys.includes(hoverKey.value)) {
      hoverKey.value = null;
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
    // The row is resolved by its own id, not by its position among the
    // scroller's children: grouped rows are grandchildren of the scroller.
    const el = document.getElementById(rowId(index));
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
  if (key === "Escape" && tipShown.value) {
    // Dismiss the visible tip. A tip the keyboard opened owns this Escape;
    // a tip the pointer opened lets Escape keep its meaning below.
    const shown = tipShown.value;
    tipDismissed.value = shown.id;
    if (shown.source === "focus") {
      consume(event);
      return;
    }
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

// Focus one row by its stable key (slice U): a service flow returns focus to
// the entry that opened it while that entry survives, else to the card's
// first valid row.
function focusRow(key) {
  const index = props.rows.findIndex((row) => row.key === key);
  setActive(index >= 0 ? index : firstEnabled(props.rows));
  focus();
}

onMounted(() => {
  if (props.autofocus) {
    focus();
  }
});

defineExpose({ focus, setActive, focusRow });
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
    :data-mapping-token="mappingToken || null"
    :aria-activedescendant="rows.length ? rowId(activeIndex) : null"
    @keydown="onKeydown"
    @focusin="cardFocused = true"
    @focusout="cardFocused = false"
    @mouseleave="hoverKey = null"
  >
    <span :class="cls('__corners')" aria-hidden="true"></span>
    <div v-if="caption" :class="cls('__caption')" aria-hidden="true">{{ caption }}</div>
    <p
      v-for="(note, index) in notes"
      :key="`note-${index}`"
      :class="cls('__note')"
      data-testid="choice-card-note"
    >{{ note }}</p>
    <div
      :key="viewKey"
      ref="scrollRef"
      :class="cls('__rows')"
      :style="{ '--row-count': rows.length }"
      @scroll.passive="onRowsScroll"
      @animationend="onRowsScroll"
    >
    <div
      v-for="group in groupedRows"
      :key="`${viewKey}-group-${group.id}`"
      :class="cls('__group')"
      :role="group.id ? 'group' : null"
      :aria-labelledby="group.label ? groupHeadingId(group) : null"
      :data-group="group.id || null"
    >
    <div
      v-if="group.label"
      :id="groupHeadingId(group)"
      :class="cls('__group-heading')"
      role="heading"
      aria-level="3"
      data-testid="choice-card-group-heading"
    >{{ group.label }}</div>
    <div
      v-for="entry in group.rows"
      :id="rowId(entry.index)"
      :key="`${viewKey}-${entry.row.key}`"
      :class="[
        cls('__row'),
        cls(`__row--${entry.row.kind || 'row'}`),
        entry.index === activeIndex ? cls('__row--active') : [],
        entry.index === trailingIndex ? cls('__row--trailing') : [],
        entry.row.lock ? cls('__row--locked') : [],
        entry.row.unread && !entry.row.lock ? cls('__row--unread') : [],
      ]"
      role="menuitem"
      :data-testid="entry.row.testId || 'choice-card-row'"
      :data-row-key="entry.row.key"
      :data-keyword-id="entry.row.keywordId"
      :data-active="entry.index === activeIndex ? 'true' : 'false'"
      :data-locked="entry.row.lock ? 'true' : null"
      :data-unread="entry.row.unread && !entry.row.lock ? 'true' : null"
      :style="{ '--row-index': entry.index }"
      :aria-disabled="entry.row.enabled === false ? 'true' : null"
      :aria-describedby="describedBy(entry.row, entry.index)"
      @click="onRowClick(entry.index)"
      @mouseenter="hoverKey = entry.row.key"
    >
      <span
        v-if="entry.row.badge || entry.row.icon"
        :class="cls('__badge')"
        aria-hidden="true"
        :data-badge="entry.row.badge"
      >
        <!-- The keyboard glyph draws tiny in the loaded text faces, so a
             keyboard badge is drawn as a small keyboard. -->
        <svg
          v-if="entry.row.icon === 'keyboard'"
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
          v-else-if="entry.row.icon === 'close'"
          :class="[cls('__badge-icon'), cls('__badge-icon--close'), entry.row.kind === 'leave' ? cls('__badge-icon--leave') : []]"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
        >
          <path d="M7 7l10 10M17 7L7 17" />
        </svg>
        <!-- A trash-can badge (the suggestions card's 清除建議): drawn in the
             dock icon vocabulary so it never reads as the ✕ of 返回. -->
        <svg
          v-else-if="entry.row.icon === 'trash'"
          :class="[cls('__badge-icon'), cls('__badge-icon--trash')]"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
          data-icon="trash"
        >
          <path d="M4.5 7h15M9.5 7V4.8h5V7M6.5 7l1 12.2h9L17.5 7M10.2 10.5v5.5M13.8 10.5v5.5" />
        </svg>
        <template v-else>{{ entry.row.badge }}</template>
      </span>
      <span :class="cls('__text')">
        <span :class="cls('__label')">{{ entry.row.label }}</span>
        <span
          v-if="entry.row.hint"
          :class="cls('__hint')"
          data-testid="choice-card-hint"
        >{{ entry.row.hint }}</span>
        <span
          v-if="entry.row.reason"
          :id="reasonId(entry.index)"
          :class="cls('__reason')"
          :data-testid="entry.row.reasonTestId || 'choice-card-reason'"
        >{{ entry.row.reason }}</span>
        <!-- A locked topic says so in text, not only by its padlock. -->
        <span v-if="entry.row.lock" :class="cls('__sr')">（尚未解鎖）</span>
        <!-- An unread topic says so in text, not only by its pip. -->
        <span v-else-if="entry.row.unread" :class="cls('__sr')">（未讀）</span>
      </span>
      <span
        v-if="entry.row.unread && !entry.row.lock"
        :class="cls('__unread')"
        data-testid="choice-card-unread"
        aria-hidden="true"
      ></span>
      <svg
        v-if="entry.row.lock"
        :class="cls('__lock')"
        data-testid="choice-card-lock"
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <rect x="5.5" y="10.5" width="13" height="9.5" rx="1.6" />
        <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5M12 14.2v2.4" />
      </svg>
    </div>
    </div>
    </div>
    <!-- The accessible copies of the rows' hints: descriptions, outside every
         menu item so they never join a row's name. The pool itself is hidden
         from the accessibility tree (no stray menu children); a hidden node
         still describes the row that references it directly. -->
    <div v-if="rows.some((row) => row.tip)" :class="cls('__sr')" aria-hidden="true">
      <template v-for="(row, index) in rows" :key="`tip-${viewKey}-${row.key}`">
        <span v-if="row.tip" :id="tipId(index)" data-testid="choice-card-tip-text">{{ row.tip }}</span>
      </template>
    </div>
    <!-- The visual hint (decorative copy of the description). -->
    <div
      v-if="tipShown"
      ref="tipRef"
      :class="[cls('__tip'), cls(`__tip--${tipPlace.side}`)]"
      data-testid="choice-card-tip"
      :data-tip-source="tipShown.source"
      :data-placed="tipPlace.placed ? 'true' : 'false'"
      :data-tip-row="rows[tipShown.index]?.key"
      aria-hidden="true"
      :style="{ top: `${tipPlace.top}px`, '--choice-tip-room': tipPlace.room === null ? null : `${tipPlace.room}px` }"
    >
      <svg
        :class="cls('__tip-icon')"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <rect x="5.5" y="10.5" width="13" height="9.5" rx="1.6" />
        <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5M12 14.2v2.4" />
      </svg>
      <span :class="cls('__tip-text')">{{ tipShown.text }}</span>
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

/* A labelled row group (slice U): the heading is a caption step above its
   rows, never a row itself -- it takes no badge, no digit, no focus and no
   hover fill, and the group is its accessible name. */
.choice-card__group {
  display: flex;
  flex-direction: column;
  gap: inherit;
}

.choice-card__group + .choice-card__group {
  margin-top: clamp(2px, 0.37vh, 4px * var(--ui-scale));
}

.choice-card__group-heading {
  flex: none;
  padding: calc(6px * var(--ui-scale)) calc(12px * var(--ui-scale)) 0;
  font: var(--text-xs) / 1.3 var(--f-sans);
  letter-spacing: 0.24em;
  color: var(--ink-400);
  text-transform: none;
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

/* A row's optional second line (a suggestion's hint): quieter than the
   label, in the command face. */
.choice-card__hint {
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  line-height: 1.45;
  color: var(--paper-400);
  overflow-wrap: anywhere;
}

/* The muted notes above the rows (the generating, degraded, and empty
   states of the suggestions card): not rows, not selectable. */
.choice-card__note {
  flex: none;
  margin: 0;
  padding: calc(10px * var(--ui-scale)) calc(26px * var(--ui-scale)) 0;
  font: var(--text-sm)/1.5 var(--f-sans);
  color: var(--paper-400);
}

.choice-card__note + .choice-card__rows {
  padding-top: calc(6px * var(--ui-scale));
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
/* Locked topics (authored-dialogue-locked-ui). A locked row is selectable:
   its label reads a step quieter and a padlock sits at the row's end, but it
   keeps the enabled row's hover and the active row's gold fill, because
   choosing it plays the host's refusal. It never takes the dashed badge of a
   disabled row. */
.choice-card__row--locked .choice-card__label {
  color: var(--paper-300);
}

.choice-card__lock {
  flex: none;
  margin-left: auto;
  width: calc(16px * var(--ui-scale));
  height: calc(16px * var(--ui-scale));
  color: var(--gold-500);
  opacity: 0.85;
}

.choice-card:focus .choice-card__row--active .choice-card__lock {
  color: var(--gold-300);
  opacity: 1;
}

/* Unread topics (authored-dialogue-unread-notices). A small gold diamond
   pip sits in the trailing status slot (the padlock's slot: a locked row
   never shows both) and the label reads one step brighter. The pip carries a
   soft halo and glows once as the row enters, then rests; shape and text
   carry the state as well as colour. */
.choice-card__row--unread .choice-card__label {
  color: var(--paper-50);
}

.choice-card__unread {
  flex: none;
  margin-left: auto;
  width: calc(8px * var(--ui-scale));
  height: calc(8px * var(--ui-scale));
  margin-right: calc(4px * var(--ui-scale));
  background: var(--gold-400);
  transform: rotate(45deg);
  border-radius: calc(1px * var(--ui-scale));
  box-shadow:
    0 0 0 calc(2px * var(--ui-scale)) rgba(228, 200, 142, 0.16),
    0 0 calc(6px * var(--ui-scale)) rgba(238, 221, 180, 0.55);
  animation: elosern-choice-unread-glint calc(var(--motion-slow) * 2) ease-out both;
  animation-delay: calc(var(--motion-stagger) * var(--row-index, 0));
}

.choice-card--still .choice-card__unread,
.choice-card--rows-still .choice-card__unread {
  animation: none;
}

.choice-card:focus .choice-card__row--active .choice-card__unread {
  background: var(--gold-300);
}

@keyframes elosern-choice-unread-glint {
  0% {
    opacity: 0;
    box-shadow: 0 0 0 0 rgba(228, 200, 142, 0);
  }
  40% {
    opacity: 1;
    box-shadow:
      0 0 0 calc(4px * var(--ui-scale)) rgba(228, 200, 142, 0.28),
      0 0 calc(12px * var(--ui-scale)) rgba(238, 221, 180, 0.8);
  }
  100% {
    opacity: 1;
  }
}

/* Text for assistive technology only: clipped, never `display: none`, so
   a description reference still resolves. */
.choice-card__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  border: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}

/* The requirement hint: one tooltip beside the card, top-aligned with its
   row (placed by the card). Never focusable; the pointer may rest on it, and
   its transparent bridge spans the gap so the move from the row onto it
   never leaves the card. The hint wraps in full, never truncated, and its
   width never exceeds the room on its side. */
.choice-card__tip {
  position: absolute;
  z-index: 2;
  top: 0;
  left: calc(100% + 10px * var(--ui-scale));
  box-sizing: border-box;
  width: max-content;
  max-width: min(calc(320px * var(--ui-scale)), var(--choice-tip-room, calc(320px * var(--ui-scale))));
  display: flex;
  align-items: flex-start;
  gap: calc(8px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(12px * var(--ui-scale));
  background: linear-gradient(180deg, rgba(27, 25, 29, 0.97), rgba(12, 13, 17, 0.97));
  border: 1px solid rgba(185, 154, 96, 0.55);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg);
  font: var(--text-sm)/1.5 var(--f-sans);
  color: var(--paper-200);
  overflow-wrap: anywhere;
  pointer-events: auto;
  animation: elosern-choice-card-in var(--motion-fast) var(--ease-standard) backwards;
}

/* Invisible until its first placement lands. */
.choice-card__tip[data-placed="false"] {
  visibility: hidden;
}

.choice-card__tip--left {
  left: auto;
  right: calc(100% + 10px * var(--ui-scale));
}

.choice-card__tip::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  right: 100%;
  width: calc(10px * var(--ui-scale) + 2px);
}

.choice-card__tip--left::before {
  right: auto;
  left: 100%;
}

.choice-card__tip-icon {
  flex: none;
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
  margin-top: calc(3px * var(--ui-scale));
  color: var(--gold-500);
}

.choice-card__tip-text {
  min-width: 0;
}
</style>
