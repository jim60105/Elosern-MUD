<script setup>
// QuestDrawer (quest-drawer-book-tab): the 任務 drawer's body — a two-level
// icon-tabbed master/detail surface. The first level (a horizontal strip
// under the drawer header) switches between the quest book and the guild
// counter. The book adds a vertical state rail (in progress, completed,
// failed) beside the list column and the detail column. The counter tab
// hosts the existing GuildCounter until quest-drawer-guild-board-tab
// replaces it.
//
// Every decision comes from quest-drawer-model.js; the tab, state, and row
// memory comes from quest-drawer-memory.js (session-scoped, keys only). The
// counter tab is disabled, yet focusable with its reason, while no usable
// guild section exists; a remembered counter tab then falls back to the book.
//
// Every intent (book actions and the hosted counter's) is forwarded as one
// `action` event carrying the exact `{action_id, payload}`.
import { computed, useId, watch } from "vue";
import GuildCounter from "./GuildCounter.vue";
import IconTabs from "./IconTabs.vue";
import QuestDetail from "./QuestDetail.vue";
import QuestList from "./QuestList.vue";
import {
  BOOK_STATES,
  bookActions,
  bookDetail,
  bookListRow,
  bookStatus,
  counterRowsById,
  counterTab,
  rowsByState,
  stateCounts,
  turninHot,
} from "./quest-drawer-model.js";
import { syncQuestDrawerMemoryScope, useQuestDrawerMemory } from "./quest-drawer-memory.js";

const props = defineProps({
  // The committed `quest_log` v2 panel (null before the first commit).
  questLog: { type: Object, default: null },
  // The committed `services` panel (null before the first commit).
  services: { type: Object, default: null },
  // `<generation>|<epoch>`: a change discards the session memory.
  memoryScope: { type: String, default: "" },
});

const emit = defineEmits(["action"]);

const memory = useQuestDrawerMemory(props.memoryScope);
watch(
  () => props.memoryScope,
  (scope) => syncQuestDrawerMemoryScope(scope),
);

const uid = useId();
const panelId = (key) => `quest-drawer-${uid}-${key}`;

// ── First level ────────────────────────────────────────────────────────
const counter = computed(() => counterTab(props.services));
const top = computed(() => (memory.top === "counter" && counter.value.enabled ? "counter" : "book"));

const topTabs = computed(() => [
  { key: "book", label: "任務簿", glyph: "quest_book", controls: panelId("book") },
  {
    key: "counter",
    label: "公會櫃檯",
    glyph: "guild_counter",
    controls: counter.value.enabled ? panelId("counter") : undefined,
    disabled: !counter.value.enabled,
    reason: counter.value.enabled ? undefined : (counter.value.reason ?? undefined),
    // The former absence markers now name the disabled tab's reason.
    reasonAttrs: counter.value.enabled
      ? undefined
      : props.services?.available === false
        ? { "data-testid": "quest-drawer__counter-unavailable", "data-reason-code": counter.value.reasonCode ?? undefined }
        : { "data-testid": "quest-drawer__counter-absent" },
  },
]);

function selectTop(key) {
  memory.top = key;
}

// ── Book: state rail ──────────────────────────────────────────────────
const status = computed(() => bookStatus(props.questLog));
const groups = computed(() => rowsByState(props.questLog));
const counts = computed(() => stateCounts(groups.value));
const counterRows = computed(() => counterRowsById(props.services));
const hot = computed(() => turninHot(groups.value, counterRows.value));

const bookState = computed(() =>
  BOOK_STATES.some((state) => state.key === memory.bookState) ? memory.bookState : "in_progress",
);
const stateMeta = computed(() => BOOK_STATES.find((state) => state.key === bookState.value));

const stateTabs = computed(() =>
  BOOK_STATES.map((state) => ({
    key: state.key,
    label: state.label,
    glyph: state.glyph,
    count: counts.value[state.key],
    hot: state.key === "completed" && hot.value,
    controls: panelId("list"),
  })),
);

function selectState(key) {
  memory.bookState = key;
}

// ── Book: list and detail ─────────────────────────────────────────────
const stateRows = computed(() => groups.value[bookState.value] ?? []);
const listRows = computed(() => stateRows.value.map(bookListRow));
const memoryKey = computed(() => `book:${bookState.value}`);

const selectedRow = computed(() => {
  const remembered = memory.selectedByTab[memoryKey.value];
  return stateRows.value.find((row) => row.quest_id === remembered) ?? stateRows.value[0] ?? null;
});

function selectRow(id) {
  memory.selectedByTab = { ...memory.selectedByTab, [memoryKey.value]: id };
}

const detail = computed(() => (selectedRow.value ? bookDetail(selectedRow.value) : null));
const actions = computed(() =>
  bookActions(selectedRow.value, selectedRow.value ? counterRows.value.get(selectedRow.value.quest_id) : null),
);

function forward(intent) {
  emit("action", intent);
}
</script>

<template>
  <section class="quest-drawer" data-testid="quest-drawer" :data-tab="top" aria-label="任務">
    <div class="quest-drawer__head">
      <IconTabs
        class="quest-drawer__top-tabs"
        data-testid="quest-drawer__top-tabs"
        orientation="horizontal"
        aria-label="任務分類"
        :tabs="topTabs"
        :model-value="top"
        @update:model-value="selectTop"
      />
    </div>

    <div
      v-if="top === 'book'"
      :id="panelId('book')"
      class="quest-drawer__body quest-drawer__body--book"
      role="tabpanel"
      aria-label="任務簿"
      data-testid="quest-drawer__book"
    >
      <IconTabs
        class="quest-drawer__rail"
        data-testid="quest-drawer__state-rail"
        orientation="vertical"
        aria-label="任務狀態"
        :tabs="stateTabs"
        :model-value="bookState"
        @update:model-value="selectState"
      />
      <QuestList
        :id="panelId('list')"
        role="tabpanel"
        :aria-label="stateMeta.label"
        :heading="stateMeta.label"
        :rows="listRows"
        :selected-id="selectedRow?.quest_id ?? null"
        :status="status"
        :reason="questLog?.reason ?? null"
        :empty-guidance="stateMeta.guidance"
        @select="selectRow"
      />
      <QuestDetail :detail="detail" :actions="actions" @action="forward" />
    </div>

    <div
      v-else
      :id="panelId('counter')"
      class="quest-drawer__body quest-drawer__body--counter"
      role="tabpanel"
      aria-label="公會櫃檯"
      data-testid="quest-drawer__counter"
    >
      <GuildCounter
        :services="services"
        @quest_register="forward"
        @quest_accept="forward"
        @exam_request="forward"
      />
    </div>
  </section>
</template>

<style scoped>
/* Frame and grid of the approved prototype's `.qd` / `.qd-body`
   (docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue). The drawer
   chrome (seal, title, close) is HudDrawer's own header (design Decision 7). */
.quest-drawer {
  --quest-drawer-line: rgba(185, 154, 96, 0.28);
  --quest-drawer-rail-w: calc(68px * var(--ui-scale));
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;
  color: var(--paper-200);
  font-family: var(--f-sans);
  background:
    radial-gradient(120% 80% at 70% 0%, rgba(185, 154, 96, 0.07), transparent 60%),
    linear-gradient(180deg, #16181dfa, #0e1014fa);
}

.quest-drawer__head {
  position: relative;
  z-index: 2;
  display: flex;
  padding: var(--sp-1) var(--sp-5) 0;
  border-bottom: 1px solid var(--quest-drawer-line);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.25), transparent);
}

.quest-drawer__top-tabs {
  align-self: flex-end;
}

.quest-drawer__body {
  min-height: 0;
}

.quest-drawer__body--book {
  display: grid;
  grid-template-columns: var(--quest-drawer-rail-w) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
}

/* The rail's tooltips open to the right over the list column. */
.quest-drawer__rail {
  position: relative;
  z-index: 1;
}

.quest-drawer__body--counter {
  overflow-y: auto;
  padding: var(--sp-5);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}
</style>
