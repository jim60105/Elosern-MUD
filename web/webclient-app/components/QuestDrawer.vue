<script setup>
// QuestDrawer (quest-drawer-book-tab): the 任務 drawer's body — a two-level
// icon-tabbed master/detail surface. The first level (a horizontal strip
// under the drawer header) switches between the quest book and the guild
// counter. The book adds a vertical state rail (in progress, completed,
// failed) beside the list column and the detail column. The counter tab
// (quest-drawer-guild-board-tab) has the same three columns for a registered
// holder: a grade rail built from the guild section's `rank_ladder`, the rank
// card above the selected grade's board offers, and the selected offer's
// detail with its accept action. An unregistered holder sees only the
// registration card.
//
// Every decision comes from quest-drawer-model.js; the tab, state, and row
// memory comes from quest-drawer-memory.js (session-scoped, keys only). The
// counter tab is disabled, yet focusable with its reason, while no usable
// guild section exists; a remembered counter tab then falls back to the book.
//
// Every intent (book, board, registration, and examination) is forwarded as one
// `action` event carrying the exact `{action_id, payload}`.
import { computed, nextTick, ref, useId, watch } from "vue";
import EmptyState from "./EmptyState.vue";
import GradeGem from "./GradeGem.vue";
import GuildRankCard from "./GuildRankCard.vue";
import IconTabs from "./IconTabs.vue";
import QuestDetail from "./QuestDetail.vue";
import QuestList from "./QuestList.vue";
import {
  BOOK_STATES,
  bookActions,
  bookDetail,
  bookListRow,
  boardBasis,
  bookStatus,
  counterRowsById,
  counterTab,
  defaultGrade,
  emptyGradeLine,
  gradeLocked,
  gradeTabs,
  holderRank,
  lockedGradeLine,
  offerActions,
  offerDetail,
  offerListRow,
  offersByGrade,
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

// ── Counter: registration or the grade-tabbed board ───────────────────
const guild = computed(() => (counter.value.enabled ? props.services.guild : null));
const registration = computed(() => guild.value?.registration ?? null);
const registered = computed(() => registration.value?.registered !== false);
const register = computed(() => registration.value?.register ?? null);

const ladder = computed(() => guild.value?.rank_ladder ?? []);
const rank = computed(() => holderRank(props.services));
const basis = computed(() => boardBasis(ladder.value, rank.value));
const offers = computed(() => offersByGrade(guild.value?.board, ladder.value));

// The remembered grade counts only under the ladder and rank it was chosen
// under; otherwise the default grade applies.
const grade = computed(() => {
  if (memory.boardBasis === basis.value && ladder.value.includes(memory.boardGrade)) return memory.boardGrade;
  return defaultGrade(ladder.value, rank.value, offers.value);
});

// Pin the shown grade once the board is on screen, so a commit that empties
// the default grade (the last offer accepted) does not move the tab.
watch(
  () => (top.value === "counter" && registered.value && guild.value ? [basis.value, grade.value] : null),
  (pair) => {
    if (pair && memory.boardBasis !== pair[0]) {
      memory.boardBasis = pair[0];
      memory.boardGrade = pair[1];
    }
  },
  { immediate: true },
);

const gradeRail = computed(() =>
  gradeTabs(ladder.value, rank.value, offers.value).map((tab) => ({ ...tab, controls: panelId("board-list") })),
);
const locked = computed(() => gradeLocked(ladder.value, rank.value, grade.value));
const gradeRows = computed(() => (locked.value ? [] : (offers.value[grade.value] ?? [])));
const offerRows = computed(() => gradeRows.value.map(offerListRow));
const offerKey = computed(() => `board:${grade.value}`);

const selectedOffer = computed(() => {
  const remembered = memory.selectedByTab[offerKey.value];
  return gradeRows.value.find((row) => row.definition_key === remembered) ?? gradeRows.value[0] ?? null;
});

function selectGrade(key) {
  memory.boardBasis = basis.value;
  memory.boardGrade = key;
}

function selectOffer(id) {
  memory.selectedByTab = { ...memory.selectedByTab, [offerKey.value]: id };
}

const offerView = computed(() => (selectedOffer.value ? offerDetail(selectedOffer.value, guild.value.branch_label) : null));
const offerBar = computed(() => offerActions(selectedOffer.value));

// A commit can unmount the focused control (the register button, or an
// accepted offer's detail). Focus then lands on <body>; return it to the
// selected tab of the open level so the drawer keeps keyboard ownership.
// Only focus that was inside the drawer before the update is rescued, so a
// background commit never pulls focus in from elsewhere.
const root = ref(null);
const focusSource = () => [registered.value, selectedOffer.value?.definition_key ?? null, selectedRow.value?.quest_id ?? null];
let focusWasInside = false;
watch(focusSource, () => {
  focusWasInside = !!root.value?.contains(document.activeElement);
}, { flush: "pre" });
watch(
  focusSource,
  async () => {
    await nextTick();
    if (!focusWasInside) return;
    const active = document.activeElement;
    if (active && active !== document.body) return;
    const rail = top.value === "counter" && registered.value ? "grade-rail" : top.value === "book" ? "state-rail" : "top-tabs";
    root.value?.querySelector(`[data-testid="quest-drawer__${rail}"] [role="tab"][tabindex="0"]`)?.focus();
  },
  { flush: "post" },
);

function forward(intent) {
  emit("action", intent);
}

function registerNow() {
  if (register.value?.enabled) forward({ action_id: register.value.action_id, payload: {} });
}
</script>

<template>
  <section ref="root" class="quest-drawer" data-testid="quest-drawer" :data-tab="top" aria-label="任務">
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
      v-else-if="registered"
      :id="panelId('counter')"
      class="quest-drawer__body quest-drawer__body--board"
      role="tabpanel"
      aria-label="公會櫃檯"
      data-testid="quest-drawer__counter"
    >
      <IconTabs
        class="quest-drawer__rail"
        data-testid="quest-drawer__grade-rail"
        orientation="vertical"
        aria-label="委託等級"
        :tabs="gradeRail"
        :model-value="grade"
        @update:model-value="selectGrade"
      >
        <template #icon="{ tab }">
          <GradeGem :grade="tab.key" size="md" />
        </template>
      </IconTabs>
      <QuestList
        :id="panelId('board-list')"
        role="tabpanel"
        :aria-label="`${grade} 級委託`"
        :heading="`${grade} 級委託`"
        :rows="offerRows"
        :selected-id="selectedOffer?.definition_key ?? null"
        :empty-headline="locked ? lockedGradeLine(grade) : emptyGradeLine(grade)"
        :empty-glyph="locked ? 'lock' : 'quests'"
        :data-locked="String(locked)"
        @select="selectOffer"
      >
        <template v-if="guild.rank" #lead>
          <GuildRankCard class="quest-drawer__rank" :rank="guild.rank" @exam_request="forward" />
        </template>
      </QuestList>
      <QuestDetail :detail="offerView" :actions="offerBar" @action="forward" />
    </div>

    <div
      v-else
      :id="panelId('counter')"
      class="quest-drawer__body quest-drawer__body--register"
      role="tabpanel"
      aria-label="公會櫃檯"
      data-testid="quest-drawer__counter"
    >
      <EmptyState
        class="quest-drawer__register-card"
        data-testid="quest-drawer__registration"
        glyph="guild_counter"
        headline="未加入公會"
        guidance="加入公會後，就能接取任務板上的委託並累積功績。"
      >
        <button
          v-if="register?.enabled"
          type="button"
          class="quest-drawer__primary"
          data-testid="quest-drawer__register"
          @click="registerNow"
        >{{ register.label }}</button>
        <p
          v-else-if="register?.disabled_reason"
          class="quest-drawer__register-reason"
          data-testid="quest-drawer__register-reason"
          :data-reason-code="register.disabled_reason.code"
        >{{ register.disabled_reason.message }}</p>
      </EmptyState>
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

.quest-drawer__body--book,
.quest-drawer__body--board {
  display: grid;
  grid-template-columns: var(--quest-drawer-rail-w) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
}

/* The rail's tooltips open to the right over the list column. */
.quest-drawer__rail {
  position: relative;
  z-index: 1;
}

.quest-drawer__rank {
  flex: none;
}

/* The registration card: centered in the whole tab body. */
.quest-drawer__body--register {
  display: grid;
  place-items: center;
  overflow-y: auto;
  padding: var(--sp-8) var(--sp-5);
}

.quest-drawer__register-card {
  width: min(100%, calc(440px * var(--ui-scale)));
  box-sizing: border-box;
}

.quest-drawer__primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: calc(160px * var(--ui-scale));
  padding: var(--sp-2) var(--sp-5);
  color: var(--paper-50);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.08em;
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  border: 1px solid var(--gold-500);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 0 14px var(--seal-glow);
  cursor: pointer;
  transition: background-color var(--motion-fast) ease;
}

.quest-drawer__primary:hover {
  background: linear-gradient(180deg, var(--seal-500), var(--seal-600));
}

.quest-drawer__primary:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.quest-drawer__register-reason {
  margin: 0;
  color: var(--paper-400);
  font-size: var(--text-sm);
}

@media (prefers-reduced-motion: reduce) {
  .quest-drawer__primary {
    transition: none;
  }
}
</style>
