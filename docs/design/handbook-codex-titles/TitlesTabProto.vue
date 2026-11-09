<script setup>
// TitlesTabProto (prototype of TitleCodexTab): the Handbook's 稱號 tab over the
// unchanged `title_codex` v1 panel. Rail = six fixed-title categories, then
// (below a divider) 異名 and, while a ballot is pending, 提名 with a hot count.
// Fixed titles are a medal wall; a locked medal keeps its name and hint (D9)
// and is selectable for its 取得條件, but its face is a dashed silhouette.
// Epithets and nominees are quest-list rows. The quest detail's footer carries
// 裝備, the two-step 移除 (only where `can_remove`), and the ballot answers.
import { computed, nextTick, ref, useId, watch } from "vue";
import IconTabs from "../../../web/webclient-app/components/IconTabs.vue";
import GradeGem from "../../../web/webclient-app/components/GradeGem.vue";
import EmptyState from "../../../web/webclient-app/components/EmptyState.vue";
import CodexEmblem from "./CodexEmblem.vue";
import TileWall from "./TileWall.vue";

const props = defineProps({
  codex: { type: Object, required: true },
  initialRail: { type: String, default: "guild" },
  initialSelection: { type: String, default: null },
  initialConfirming: { type: Boolean, default: false },
});
const emit = defineEmits(["intent"]);
const uid = useId();

const CATEGORIES = [
  { key: "combat", label: "戰鬥" },
  { key: "spell", label: "法術" },
  { key: "explore", label: "探索" },
  { key: "guild", label: "公會" },
  { key: "clergy", label: "聖職" },
  { key: "romance", label: "風流韻事", short: "韻事" },
];

const fixed = computed(() => props.codex.fixed_rows);
const epithets = computed(() => props.codex.epithet_rows);
const ballot = computed(() => props.codex.pending_ballot);

const railTabs = computed(() => [
  ...CATEGORIES.map((c) => {
    const rows = fixed.value.filter((r) => r.category === c.key);
    const have = rows.filter((r) => r.unlocked).length;
    return { key: c.key, label: c.short ?? c.label, count: have, controls: `titles-${uid}-body` };
  }),
  { key: "epithet", label: "異名", count: epithets.value.length, controls: `titles-${uid}-body` },
  ...(ballot.value.length
    ? [{ key: "ballot", label: "提名", count: ballot.value.length, hot: true, controls: `titles-${uid}-body` }]
    : []),
]);

const rail = ref(props.initialRail);
const railLabel = computed(() =>
  rail.value === "epithet" ? "異名" : rail.value === "ballot" ? "提名中" : CATEGORIES.find((c) => c.key === rail.value)?.label,
);
const isFixed = computed(() => CATEGORIES.some((c) => c.key === rail.value));

const gradeOf = (row) => (row.category === "guild" ? (row.key.match(/^g_([a-z])_rank$/)?.[1] ?? "").toUpperCase() || null : null);

const fixedRows = computed(() => fixed.value.filter((r) => r.category === rail.value));
const medalGroups = computed(() => [
  {
    key: rail.value,
    label: null,
    items: fixedRows.value.map((row) => ({
      id: row.key,
      selectable: true,
      label: `${row.display}，${row.unlocked ? (props.codex.equipped.fixed === row.key ? "裝備中" : "已取得") : "未取得"}`,
      row,
    })),
  },
]);

const selected = ref(props.initialSelection);
const confirming = ref(props.initialConfirming);
watch(rail, () => {
  selected.value = null;
  confirming.value = false;
});
const currentId = computed(() => {
  if (isFixed.value) {
    const ids = fixedRows.value.map((r) => r.key);
    return ids.includes(selected.value) ? selected.value : (fixedRows.value.find((r) => r.unlocked)?.key ?? ids[0] ?? null);
  }
  const rows = rail.value === "epithet" ? epithets.value : ballot.value;
  const ids = rows.map((r) => r.display);
  return ids.includes(selected.value) ? selected.value : (ids[0] ?? null);
});

const detail = computed(() => {
  const id = currentId.value;
  if (!id) return null;
  if (isFixed.value) {
    const row = fixedRows.value.find((r) => r.key === id);
    const equipped = props.codex.equipped.fixed === row.key;
    return {
      kind: "fixed",
      row,
      name: row.display,
      ribbon: `${railLabel.value}稱號`,
      emblem: row.category,
      grade: gradeOf(row),
      unlocked: row.unlocked,
      stamp: !row.unlocked ? { kind: "locked", label: "未取得" } : equipped ? { kind: "equipped", label: "裝備中" } : null,
      subtitle: row.unlocked ? row.flavor : "",
      sections: row.unlocked ? [] : [{ label: "取得條件", text: row.hint || "—" }],
      equipped,
    };
  }
  if (rail.value === "epithet") {
    const row = epithets.value.find((r) => r.display === id);
    return {
      kind: "epithet",
      row,
      name: row.display,
      ribbon: "異名",
      emblem: "epithet",
      grade: null,
      unlocked: true,
      stamp: row.equipped ? { kind: "equipped", label: "裝備中" } : null,
      subtitle: row.basis,
      sections: [],
      equipped: row.equipped,
    };
  }
  const index = ballot.value.findIndex((r) => r.display === id);
  const row = ballot.value[index];
  return {
    kind: "ballot",
    row,
    index,
    name: row.display,
    ribbon: "異名提名",
    emblem: "ballot",
    grade: null,
    unlocked: true,
    stamp: { kind: "pending", label: "提名中" },
    subtitle: row.basis,
    sections: [],
    equipped: false,
  };
});

const bar = computed(() => {
  const d = detail.value;
  if (!d) return { actions: [], reason: null };
  if (d.kind === "fixed") {
    return {
      reason: d.unlocked ? (d.equipped ? "★ 目前裝備中" : null) : "尚未取得，無法裝備",
      actions: [
        {
          key: "equip",
          label: d.equipped ? "已裝備" : "裝備",
          enabled: d.unlocked && !d.equipped,
          reason: d.unlocked ? (d.equipped ? "目前已裝備" : null) : "尚未取得",
          tone: "primary",
        },
      ],
    };
  }
  if (d.kind === "epithet") {
    if (confirming.value) {
      return {
        reason: "移除後無法恢復，確定要移除這個異名嗎？",
        actions: [
          { key: "cancel", label: "取消", tone: "ghost" },
          { key: "confirm-remove", label: "確認移除", tone: "primary" },
        ],
      };
    }
    return {
      reason: d.equipped ? "★ 目前裝備中" : null,
      actions: [
        ...(d.row.can_remove ? [{ key: "remove", label: "移除…", tone: "ghost" }] : []),
        { key: "equip", label: d.equipped ? "已裝備" : "裝備", enabled: !d.equipped, reason: d.equipped ? "目前已裝備" : null, tone: "primary" },
      ],
    };
  }
  return {
    reason: null,
    actions: [
      { key: "decline", label: "放棄提名", tone: "ghost" },
      { key: "accept", label: "接受此異名", tone: "primary" },
    ],
  };
});

function onAction(key) {
  const d = detail.value;
  if (key === "equip") {
    emit("intent", { action_id: "title.equip", payload: d.kind === "fixed" ? { kind: "fixed", identifier: d.row.key } : { kind: "epithet", identifier: d.row.display } });
  } else if (key === "remove") {
    confirming.value = true;
  } else if (key === "cancel") {
    confirming.value = false;
  } else if (key === "confirm-remove") {
    confirming.value = false;
    emit("intent", { action_id: "title.remove", payload: { display: d.row.display } });
  } else if (key === "accept") {
    emit("intent", { action_id: "title.accept", payload: { index: d.index + 1 } });
  } else if (key === "decline") {
    emit("intent", { action_id: "title.decline", payload: {} });
  }
}

// The host's closeGuard: an armed removal is cancelled instead of closing.
function guardClose() {
  if (confirming.value) {
    confirming.value = false;
    return false;
  }
  return true;
}
defineExpose({ guardClose });

// ---- Row list (epithets, nominees): the quest list's roving listbox.
const rows = computed(() => (rail.value === "epithet" ? epithets.value : rail.value === "ballot" ? ballot.value : []));
const rowEls = new Map();
function onRowKey(event) {
  const ids = rows.value.map((r) => r.display);
  const i = ids.indexOf(currentId.value);
  const next = { ArrowDown: i + 1, ArrowUp: i - 1, Home: 0, End: ids.length - 1 }[event.key];
  if (next === undefined) return;
  event.preventDefault();
  selectRow(ids[Math.max(0, Math.min(ids.length - 1, next))]);
  nextTick(() => rowEls.get(currentId.value)?.focus());
}
function selectRow(id) {
  selected.value = id;
  confirming.value = false;
}
</script>

<template>
  <div class="hb-titles" data-testid="handbook__titles">
    <IconTabs
      class="hb-titles__rail"
      orientation="vertical"
      aria-label="稱號分類"
      show-labels
      :tabs="railTabs"
      :model-value="rail"
      @update:model-value="(key) => (rail = key)"
    >
      <template #icon="{ tab }">
        <CodexEmblem :name="tab.key" />
      </template>
    </IconTabs>

    <div :id="`titles-${uid}-body`" class="hb-col" role="tabpanel" :aria-label="railLabel">
      <header class="hb-col__head">
        <span class="hb-col__kicker">{{ railLabel }}</span>
        <span class="hb-col__rule" aria-hidden="true"></span>
        <span v-if="isFixed" class="hb-col__n">
          <b>{{ fixedRows.filter((r) => r.unlocked).length }}</b> / {{ fixedRows.length }}
        </span>
        <span v-else class="hb-col__n">{{ rows.length }}</span>
      </header>

      <template v-if="isFixed">
        <TileWall
          v-if="fixedRows.length"
          variant="medal"
          :groups="medalGroups"
          :selected-id="currentId"
          :aria-label="`${railLabel}稱號`"
          @select="(id) => (selected = id)"
        >
          <template #tile="{ item, selected: isSel }">
            <div class="hb-medal" :class="{ 'is-selected': isSel, 'is-locked': !item.row.unlocked }">
              <span class="hb-medal__disc">
                <template v-if="item.row.unlocked">
                  <GradeGem v-if="gradeOf(item.row)" :grade="gradeOf(item.row)" size="md" />
                  <span v-else class="hb-medal__emblem"><CodexEmblem :name="item.row.category" :stroke-width="1.4" /></span>
                </template>
                <svg v-else class="hb-medal__lock" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M8 11V8a4 4 0 0 1 8 0v3M5.5 11h13v9.5h-13zM12 14.5v2.5" stroke="currentColor" stroke-width="1.6" />
                </svg>
                <span v-if="codex.equipped.fixed === item.row.key" class="hb-medal__eq" aria-hidden="true">★</span>
              </span>
              <span class="hb-medal__name">{{ item.row.display }}</span>
            </div>
          </template>
        </TileWall>
        <p v-else class="hb-col__note">這個分類還沒有可收集的稱號。</p>
      </template>

      <ul v-else class="hb-rows" role="listbox" :aria-label="railLabel" @keydown="onRowKey">
        <li
          v-for="row in rows"
          :key="row.display"
          :ref="(el) => (el ? rowEls.set(row.display, el) : rowEls.delete(row.display))"
          role="option"
          class="hb-row"
          :class="{ 'is-selected': row.display === currentId }"
          :tabindex="row.display === currentId ? 0 : -1"
          :aria-selected="String(row.display === currentId)"
          @click="selectRow(row.display)"
        >
          <span class="hb-row__glyph" aria-hidden="true"><CodexEmblem :name="rail === 'ballot' ? 'ballot' : 'epithet'" /></span>
          <span class="hb-row__main">
            <span class="hb-row__name">{{ row.display }}</span>
            <span class="hb-row__basis">{{ row.basis }}</span>
          </span>
          <span v-if="row.equipped" class="hb-row__eq">★ 裝備中</span>
        </li>
      </ul>
    </div>

    <article v-if="detail" :key="`${rail}:${currentId}`" class="hb-detail">
      <div class="hb-detail__scroll">
        <div class="hb-hero">
          <span class="hb-hero__medal" :class="{ 'is-locked': !detail.unlocked }">
            <template v-if="detail.unlocked">
              <GradeGem v-if="detail.grade" :grade="detail.grade" size="lg" />
              <span v-else class="hb-hero__emblem"><CodexEmblem :name="detail.emblem" :stroke-width="1.1" /></span>
            </template>
            <svg v-else class="hb-hero__lock" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M8 11V8a4 4 0 0 1 8 0v3M5.5 11h13v9.5h-13zM12 14.5v2.5" stroke="currentColor" stroke-width="1.2" />
            </svg>
          </span>
          <span v-if="detail.stamp" class="hb-stamp" :class="`hb-stamp--${detail.stamp.kind}`">{{ detail.stamp.label }}</span>
        </div>

        <header class="hb-head">
          <span class="hb-ribbon">
            <span class="hb-ribbon__glyph"><CodexEmblem :name="detail.emblem" /></span>
            {{ detail.ribbon }}
          </span>
          <h3 class="hb-title" :class="{ 'is-locked': !detail.unlocked }">{{ detail.name }}</h3>
          <p v-if="detail.subtitle" class="hb-subtitle">{{ detail.subtitle }}</p>
        </header>

        <section v-for="section in detail.sections" :key="section.label" class="hb-letter">
          <h4 class="hb-label">{{ section.label }}</h4>
          <p class="hb-letter__text">{{ section.text }}</p>
        </section>

      </div>
      <footer class="hb-actions" :class="{ 'hb-actions--confirm': confirming }">
        <p v-if="bar.reason" class="hb-why" :class="{ 'hb-why--danger': confirming }" :role="confirming ? 'alert' : undefined">{{ bar.reason }}</p>
        <template v-for="action in bar.actions" :key="action.key">
          <span v-if="action.tone === 'primary' && !bar.reason" class="hb-spacer"></span>
          <button
            type="button"
            class="hb-btn"
            :class="[`hb-btn--${action.tone}`, { 'is-disabled': action.enabled === false }]"
            :aria-disabled="action.enabled === false ? 'true' : undefined"
            :title="action.reason || undefined"
            @click="action.enabled === false ? null : onAction(action.key)"
          >{{ action.label }}</button>
        </template>
      </footer>
    </article>
    <div v-else class="hb-detail hb-detail--empty">
      <EmptyState glyph="codex" headline="尚未取得任何異名" guidance="旅途中的事蹟被眾人傳頌時，會在這裡獲得提名。" />
    </div>
  </div>
</template>

<style scoped>
.hb-titles {
  display: grid;
  grid-template-columns: calc(68px * var(--ui-scale)) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
  min-height: 0;
  height: 100%;
}

.hb-titles__rail {
  position: relative;
  z-index: 1;
}

/* The divider before 異名: a hairline above the seventh tab. */
.hb-titles__rail :deep([data-tab-key="epithet"]) {
  margin-top: var(--sp-3);
}

.hb-titles__rail :deep([data-tab-key="epithet"])::before {
  content: "";
  position: absolute;
  top: calc(-1 * var(--sp-2));
  left: 22%;
  right: 22%;
  height: 1px;
  background: rgba(185, 154, 96, 0.35);
}

.hb-col {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-4);
  background: #15171c;
  border-right: 1px solid rgba(185, 154, 96, 0.28);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.hb-col__head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.hb-col__kicker {
  color: var(--gold-400);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.12em;
}

.hb-col__rule {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

.hb-col__n {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.hb-col__n b {
  color: var(--gold-300);
  font-size: var(--text-md);
  font-weight: 500;
}

.hb-col__note {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-400);
  font-size: var(--text-md);
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

/* ---- Medal wall */
.hb-medal {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-2) 0;
  border-radius: var(--radius-sm);
}

.hb-medal.is-selected {
  background: linear-gradient(180deg, rgba(169, 50, 42, 0.26), transparent);
}

.hb-medal__disc {
  position: relative;
  display: grid;
  place-items: center;
  width: calc(60px * var(--ui-scale));
  height: calc(60px * var(--ui-scale));
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #5c4c2c, #1a160f 70%);
  border: 2px solid var(--gold-500);
  box-shadow: 0 0 0 3px #15171c, 0 0 0 4px var(--gold-600);
  transition: box-shadow var(--motion-fast) ease;
}

.hb-medal.is-selected .hb-medal__disc {
  box-shadow: 0 0 0 3px #15171c, 0 0 0 5px var(--seal-400), 0 0 16px var(--seal-glow);
}

.hb-medal__emblem {
  width: 56%;
  height: 56%;
  color: var(--gold-300);
}

.hb-medal.is-locked .hb-medal__disc {
  background: repeating-linear-gradient(45deg, #121418 0 5px, #17191e 5px 10px);
  border: 2px dashed var(--ink-600);
  box-shadow: none;
}

.hb-medal.is-locked.is-selected .hb-medal__disc {
  box-shadow: 0 0 0 3px #15171c, 0 0 0 5px var(--seal-400);
}

.hb-medal__lock {
  width: 40%;
  height: 40%;
  color: var(--paper-700);
}

.hb-medal__eq {
  position: absolute;
  right: -4px;
  bottom: -4px;
  display: grid;
  place-items: center;
  width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
  color: var(--ink-950);
  font-size: var(--text-xs);
  background: var(--gold-400);
  border: 2px solid #15171c;
  border-radius: 50%;
}

.hb-medal__name {
  max-width: 100%;
  overflow: hidden;
  color: var(--paper-100);
  font: var(--text-xs) / 1.3 var(--f-serif);
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hb-medal.is-locked .hb-medal__name {
  color: var(--paper-500);
}

/* ---- Rows (epithets, nominees): the quest list's row language. */
.hb-rows {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.hb-row {
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
}

.hb-row:hover {
  background: rgba(255, 255, 255, 0.025);
}

.hb-row:focus-visible {
  box-shadow: var(--focus);
}

.hb-row.is-selected {
  background: linear-gradient(90deg, rgba(169, 50, 42, 0.32), rgba(185, 154, 96, 0.08) 70%, transparent);
  border-color: rgba(207, 68, 68, 0.35);
}

.hb-row.is-selected::before {
  content: "";
  position: absolute;
  left: 0;
  top: 18%;
  bottom: 18%;
  width: 3px;
  background: var(--seal-500);
  border-radius: 0 2px 2px 0;
}

.hb-row__glyph {
  width: calc(24px * var(--ui-scale));
  height: calc(24px * var(--ui-scale));
  color: var(--gold-500);
}

.hb-row__main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.hb-row__name {
  color: var(--paper-50);
  font: var(--text-md) var(--f-serif);
}

.hb-row__basis {
  overflow: hidden;
  color: var(--paper-500);
  font-size: var(--text-xs);
  white-space: nowrap;
  text-overflow: ellipsis;
}

.hb-row__eq {
  color: var(--gold-400);
  font-size: var(--text-xs);
  white-space: nowrap;
}

/* ---- Detail (shares the codex detail's language). */
.hb-detail {
  position: relative;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 0;
  height: 100%;
  background:
    radial-gradient(90% 60% at 100% 0%, rgba(169, 50, 42, 0.08), transparent 70%),
    #121418;
  animation: hb-in var(--motion-reveal) ease-out;
}

.hb-detail--empty {
  grid-template-rows: 1fr;
  place-items: center;
}

@keyframes hb-in {
  from {
    opacity: 0;
    transform: translateX(6px);
  }
}

.hb-detail__scroll {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  min-height: 0;
  overflow-y: auto;
  padding: 0 var(--sp-8) var(--sp-6);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.hb-detail__scroll > * {
  flex-shrink: 0;
}

.hb-hero {
  position: relative;
  display: grid;
  place-items: center;
  height: calc(190px * var(--ui-scale));
  margin: 0 calc(-1 * var(--sp-8));
  background:
    radial-gradient(40% 70% at 50% 55%, rgba(228, 200, 142, 0.16), transparent 70%),
    radial-gradient(70% 90% at 50% 60%, #2c261b, #121418 75%);
  border-bottom: 1px solid rgba(185, 154, 96, 0.2);
}

.hb-hero__medal {
  display: grid;
  place-items: center;
  width: calc(116px * var(--ui-scale));
  height: calc(116px * var(--ui-scale));
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #6a5631, #1a160f 70%);
  border: 3px solid var(--gold-400);
  box-shadow: 0 0 0 7px #121418, 0 0 0 8px var(--gold-600), 0 0 44px rgba(228, 200, 142, 0.25);
}

.hb-hero__medal.is-locked {
  background: repeating-linear-gradient(45deg, #121418 0 7px, #17191e 7px 14px);
  border: 3px dashed var(--ink-600);
  box-shadow: none;
}

.hb-hero__emblem {
  width: 58%;
  height: 58%;
  color: var(--gold-300);
}

.hb-hero__lock {
  width: 40%;
  height: 40%;
  color: var(--paper-700);
}

.hb-stamp {
  position: absolute;
  right: var(--sp-8);
  bottom: var(--sp-5);
  padding: 2px var(--sp-3);
  font: var(--text-xl) var(--f-display);
  letter-spacing: 0.3em;
  border-radius: var(--radius-sm);
  transform: rotate(-12deg);
  background: rgba(11, 13, 16, 0.55);
  pointer-events: none;
}

.hb-stamp--equipped {
  color: var(--gold-300);
  border: 3px double var(--gold-500);
}

.hb-stamp--locked {
  color: var(--paper-400);
  border: 2px dashed var(--paper-500);
}

.hb-stamp--pending {
  color: var(--seal-400);
  border: 3px double var(--seal-500);
}

.hb-head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.hb-ribbon {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 3px calc(22px * var(--ui-scale)) 3px var(--sp-3);
  color: var(--paper-50);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.12em;
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  clip-path: polygon(0 0, 100% 0, calc(100% - 10px) 50%, 100% 100%, 0 100%);
}

.hb-ribbon__glyph {
  width: 1.1em;
  height: 1.1em;
  color: var(--gold-300);
}

.hb-title {
  margin: var(--sp-1) 0 0;
  color: var(--paper-50);
  font: var(--text-3xl) / 1.25 var(--f-display);
  letter-spacing: 0.04em;
}

.hb-title.is-locked {
  color: var(--paper-400);
}

.hb-subtitle {
  margin: 0;
  color: var(--gold-400);
  font: var(--text-lg) / 1.5 var(--f-serif);
}

.hb-label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-2);
  color: var(--gold-500);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.18em;
}

.hb-label::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

.hb-letter {
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
  background: linear-gradient(135deg, rgba(185, 154, 96, 0.09), rgba(185, 154, 96, 0.02) 60%);
  border: 1px solid rgba(185, 154, 96, 0.28);
  border-left: 3px solid var(--gold-500);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.hb-letter__text {
  margin: 0;
  color: var(--paper-200);
  font: var(--text-sm) / 1.9 var(--f-serif);
}

.hb-plate__text {
  margin: 0;
  color: var(--gold-300);
  font: var(--text-xl) var(--f-display);
  letter-spacing: 0.1em;
}

/* The quest detail's action footer (QuestDetail .quest-detail__actions). */
.hb-actions {
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

.hb-actions--confirm {
  background: linear-gradient(90deg, rgba(124, 32, 38, 0.35), rgba(0, 0, 0, 0.4));
}

.hb-spacer {
  flex: 1;
}

.hb-why {
  margin: 0 auto 0 0;
  color: var(--paper-400);
  font-size: var(--text-sm);
}

.hb-why--danger {
  color: var(--seal-400);
}

.hb-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--sp-2) var(--sp-5);
  color: var(--paper-100);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.08em;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.hb-btn:hover:not(.is-disabled) {
  color: var(--paper-50);
  border-color: var(--gold-500);
}

.hb-btn:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.hb-btn.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hb-btn--primary {
  min-width: calc(160px * var(--ui-scale));
  color: var(--paper-50);
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  border-color: var(--gold-500);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 0 14px var(--seal-glow);
}

.hb-btn--ghost {
  color: var(--paper-400);
  background: transparent;
  border-color: transparent;
}

@media (prefers-reduced-motion: reduce) {
  .hb-detail {
    animation: none;
  }
}
</style>
