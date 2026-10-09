<script setup>
// QuestList (quest-drawer-book-tab): the quest drawer's list column — a
// heading with the row count, then a single-selection listbox of quest rows
// (category glyph, name with the tracked flag, grade gem, and either the
// in-progress bar or the issuer line), or one of the honest non-list forms:
// the absent line before the first commit, the panel's own unavailable
// reason, or the shared empty guidance. The guild board passes its offer rows
// (quest-drawer-guild-board-tab) and puts the rank card in the `lead` slot
// above the heading.
//
// Keyboard (design Decision 8): one roving tab stop on the selected row (the
// first row when nothing is selected); ArrowUp/ArrowDown/Home/End move focus
// and Enter, Space, or a click selects. Selection never follows focus alone.
import { computed, nextTick, ref, watch } from "vue";
import EmptyState from "./EmptyState.vue";
import GradeGem from "./GradeGem.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";

const props = defineProps({
  heading: { type: String, required: true },
  // bookListRow view models (quest-drawer-model.js).
  rows: { type: Array, default: () => [] },
  selectedId: { type: String, default: null },
  // "absent" | "unavailable" | "available"
  status: { type: String, default: "available" },
  // The unavailable panel's `{code, message}` reason.
  reason: { type: Object, default: null },
  emptyHeadline: { type: String, default: "這裡還沒有任務。" },
  emptyGuidance: { type: String, default: "" },
  emptyGlyph: { type: String, default: "quests" },
  ariaLabel: { type: String, default: "任務" },
});

const emit = defineEmits(["select"]);

const ids = computed(() => props.rows.map((row) => row.id));
const showRows = computed(() => props.status === "available" && props.rows.length > 0);

const focusId = ref(props.selectedId);
const rovingId = computed(() => {
  if (ids.value.includes(focusId.value)) return focusId.value;
  if (ids.value.includes(props.selectedId)) return props.selectedId;
  return ids.value[0] ?? null;
});

watch(
  () => props.selectedId,
  (value) => {
    focusId.value = value;
  },
);

const options = {};
function setOption(id, el) {
  if (el) options[id] = el;
  else delete options[id];
}

function select(id) {
  if (id != null && id !== props.selectedId) emit("select", id);
}

function optionIdOf(event) {
  return event.target?.closest?.('[role="option"]')?.dataset.questId ?? null;
}

async function focusRow(id) {
  focusId.value = id;
  await nextTick();
  options[id]?.focus();
}

function onKeydown(event) {
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  const current = optionIdOf(event);
  if (current == null) return;
  const index = ids.value.indexOf(current);
  const last = ids.value.length - 1;
  let target = null;
  switch (event.key) {
    case "ArrowDown":
      target = Math.min(index + 1, last);
      break;
    case "ArrowUp":
      target = Math.max(index - 1, 0);
      break;
    case "Home":
      target = 0;
      break;
    case "End":
      target = last;
      break;
    case "Enter":
    case " ":
      event.preventDefault();
      select(current);
      return;
    default:
      return;
  }
  event.preventDefault();
  focusRow(ids.value[target]);
}

function onFocusin(event) {
  const id = optionIdOf(event);
  if (id != null) focusId.value = id;
}

function onFocusout(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) focusId.value = props.selectedId;
}
</script>

<template>
  <div class="quest-list" data-testid="quest-drawer__list">
    <slot name="lead" />
    <header class="quest-list__head">
      <span class="quest-list__kicker">{{ heading }}</span>
      <span class="quest-list__rule" aria-hidden="true"></span>
      <span class="quest-list__n" data-testid="quest-drawer__list-count">{{ status === "available" ? rows.length : "—" }}</span>
    </header>

    <p v-if="status === 'absent'" class="quest-list__note" data-testid="quest-drawer__absent">
      尚未取得任務簿資料
    </p>
    <p
      v-else-if="status === 'unavailable'"
      class="quest-list__note"
      data-testid="quest-drawer__unavailable"
      :data-reason-code="reason?.code"
    >
      {{ reason?.message }}
    </p>
    <ul
      v-else-if="showRows"
      class="quest-list__rows"
      role="listbox"
      :aria-label="ariaLabel"
      @keydown="onKeydown"
      @focusin="onFocusin"
      @focusout="onFocusout"
    >
      <li
        v-for="row in rows"
        :key="row.id"
        :ref="(el) => setOption(row.id, el)"
        role="option"
        class="quest-list__row"
        :class="[`is-${row.state}`, { 'is-selected': row.id === selectedId }]"
        :tabindex="row.id === rovingId ? 0 : -1"
        :aria-selected="String(row.id === selectedId)"
        :data-quest-id="row.id"
        :data-testid="`quest-drawer__row--${row.id}`"
        @click="select(row.id)"
        @keyup.space.prevent
      >
        <span class="quest-list__cat" aria-hidden="true">
          <svg v-if="row.glyph && glyphPath(row.glyph)" viewBox="0 0 24 24" fill="none">
            <path :d="glyphPath(row.glyph)" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs(row.glyph)" />
          </svg>
        </span>
        <span class="quest-list__main">
          <span class="quest-list__name">
            <span class="quest-list__name-text">{{ row.name }}</span>
            <svg
              v-if="row.tracked"
              class="quest-list__pin"
              viewBox="0 0 24 24"
              role="img"
              aria-label="追蹤中"
              data-testid="quest-drawer__row-tracked"
            >
              <path :d="glyphPath('track_flag')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('track_flag')" />
            </svg>
          </span>
          <span v-if="row.progress" class="quest-list__prog">
            <span class="quest-list__bar" aria-hidden="true"><span :style="{ width: `${row.progress.pct}%` }"></span></span>
            <span class="quest-list__num">{{ row.progress.value }}/{{ row.progress.target }}</span>
          </span>
          <span v-else class="quest-list__sub">{{ row.sub }}</span>
        </span>
        <GradeGem v-if="row.grade" :grade="row.grade" size="sm" :label="`${row.grade} 級`" />
      </li>
    </ul>
    <EmptyState
      v-else
      class="quest-list__empty"
      data-testid="quest-drawer__empty"
      :glyph="emptyGlyph"
      :headline="emptyHeadline"
      :guidance="emptyGuidance"
    />
  </div>
</template>

<style scoped>
/* Port of the approved prototype's `.qd-list` / `.qd-row` rules
   (docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue). */
.quest-list {
  --quest-list-line: rgba(185, 154, 96, 0.28);
  --quest-list-line-soft: rgba(185, 154, 96, 0.14);
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  box-sizing: border-box;
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  padding: var(--sp-4);
  background: #15171c;
  border-right: 1px solid var(--quest-list-line);
  font-family: var(--f-sans);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.quest-list__head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.quest-list__kicker {
  color: var(--gold-400);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.12em;
}

.quest-list__rule {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--quest-list-line), transparent);
}

.quest-list__n {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.quest-list__note {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-400);
  font-size: var(--text-md);
  line-height: 1.7;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.quest-list__rows {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.quest-list__row {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-3) var(--sp-3) var(--sp-4);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  outline: none;
  transition: background-color var(--motion-fast) ease, border-color var(--motion-fast) ease;
}

.quest-list__row::after {
  content: "";
  position: absolute;
  left: var(--sp-4);
  right: var(--sp-3);
  bottom: -2px;
  height: 1px;
  background: repeating-linear-gradient(90deg, var(--quest-list-line-soft) 0 4px, transparent 4px 8px);
}

.quest-list__row:last-child::after {
  display: none;
}

.quest-list__row:hover {
  background: rgba(255, 255, 255, 0.025);
}

.quest-list__row:focus-visible {
  box-shadow: var(--focus);
}

.quest-list__row.is-selected {
  background: linear-gradient(90deg, rgba(169, 50, 42, 0.32), rgba(185, 154, 96, 0.08) 70%, transparent);
  border-color: rgba(207, 68, 68, 0.35);
}

.quest-list__row.is-selected::before {
  content: "";
  position: absolute;
  left: 0;
  top: 18%;
  bottom: 18%;
  width: 3px;
  background: var(--seal-500);
  border-radius: 0 2px 2px 0;
}

.quest-list__cat {
  display: grid;
  place-items: center;
  width: calc(30px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  color: var(--gold-500);
}

.quest-list__cat svg {
  width: 80%;
  height: 80%;
}

.quest-list__row.is-selected .quest-list__cat {
  color: var(--gold-300);
}

.quest-list__main {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.quest-list__name {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
  color: var(--paper-50);
  font: var(--text-md) var(--f-serif);
}

.quest-list__name-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quest-list__row.is-failed .quest-list__name {
  color: var(--paper-400);
}

.quest-list__pin {
  flex: none;
  width: calc(16px * var(--ui-scale));
  height: calc(16px * var(--ui-scale));
  color: var(--seal-400);
  fill: rgba(207, 68, 68, 0.35);
}

.quest-list__prog {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.quest-list__bar {
  flex: 1;
  height: 4px;
  overflow: hidden;
  background: #0b0d10;
  border-radius: 4px;
  box-shadow: inset 0 0 0 1px var(--ink-700);
}

.quest-list__bar > span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--gold-600), var(--gold-400));
}

.quest-list__num {
  color: var(--paper-400);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.quest-list__sub {
  overflow: hidden;
  color: var(--paper-500);
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .quest-list__row {
    transition: none;
  }
}
</style>
