<script setup>
// QuestLog (quest-issuer-model change 11, design D2/D3): the player's own
// quest book — the host-free half of the split quest drawer. It renders only
// the committed `quest_log` v1 payload (every stored record, grouped by state,
// issuer labelled per row) and invents nothing.
//
// Per-row actions:
// - Tracking comes from the row's own always-enabled `track` descriptor
//   (`guild.quest_track` is host-independent by contract), so the control is
//   present regardless of any local service host; non-in-progress rows render
//   it disabled with the stable reason.
// - Abandon and turn-in are counter-only actions: they render only from a
//   `services.guild.quests` row matching by `quest_id` — the single merge
//   point between the two panels — and mirror that descriptor's enabled
//   state, label, and disabled reason exactly. The book never synthesizes a
//   descriptor and never enables one the counter disabled. Abandon keeps the
//   explicit two-step confirmation the counter path already required.
import { computed, ref } from "vue";

const props = defineProps({
  // The committed `quest_log` v1 panel payload (or null before first commit).
  questLog: { type: Object, default: null },
  // The committed `services` v4 panel payload, read ONLY for the guild
  // section's quest rows (the counter-action merge). Never rendered directly.
  services: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["quest_track", "quest_abandon", "quest_turnin"]);

// Two-level honesty, matching the lore-codex-drawer precedent: the
// registry-owned unavailable form carries its reason; a null prop (panel not
// yet committed) renders a fixed absent line; `rows: []` is an explicit
// empty book. No invented rows in any state.
const unavailable = computed(() => props.questLog?.available === false);
const absent = computed(() => !props.questLog);
const rows = computed(() =>
  unavailable.value ? [] : (props.questLog?.rows ?? []),
);

// The counter side of the merge: a lookup of the guild section's quest rows
// by `quest_id`. A services panel that is unavailable or carries no guild
// section contributes no rows, so no counter action renders anywhere.
const counterRowsById = computed(() => {
  const guild =
    props.services?.available === false
      ? null
      : (props.services?.guild ?? null);
  const map = new Map();
  for (const row of guild?.quests ?? []) {
    if (row && typeof row.quest_id === "string") {
      map.set(row.quest_id, row);
    }
  }
  return map;
});

function counterRowFor(questId) {
  return counterRowsById.value.get(questId) ?? null;
}

// Rows grouped by the bounded stored states, panel order preserved within
// each group. Empty groups render nothing.
const STATE_GROUPS = [
  { key: "in_progress", label: "進行中" },
  { key: "completed", label: "已完成" },
  { key: "failed", label: "失敗" },
];

const groups = computed(() =>
  STATE_GROUPS.map((group) => ({
    ...group,
    rows: rows.value.filter((row) => row.state === group.key),
  })).filter((group) => group.rows.length > 0),
);

// Issuer kind label: a guild commission vs a private (npc) one. The issuer's
// display label itself always comes from the row.
const ISSUER_KIND_LABELS = { guild: "公會", npc: "委託" };

function issuerKindLabel(kind) {
  return ISSUER_KIND_LABELS[kind] ?? kind;
}

// Settlement indication: a counter quest must be claimed at the counter; an
// auto (private) quest settles inside the completing transaction. A null
// settlement (unresolvable issuance) renders nothing, exactly like its
// paired null reward_line.
const SETTLEMENT_LABELS = {
  counter: "獎勵需回櫃台領取",
  auto: "獎勵完成即結算",
};

function settlementLabel(settlement) {
  return SETTLEMENT_LABELS[settlement] ?? null;
}

// The non-in-progress tracking truth: the panel's `track` descriptor is
// always enabled by contract, so the disabled state for a terminal row is
// derived client-side with the stable reason (the quest-board precedent).
const TRACK_LOCKED_REASON = "非進行中任務無法追蹤";

function trackDescriptorFor(row) {
  return row?.track ?? null;
}

function dispatchTrack(row, tracked) {
  const descriptor = trackDescriptorFor(row);
  if (!descriptor || !descriptor.enabled) return;
  emit("quest_track", {
    action_id: descriptor.action_id,
    payload: { quest_id: row.quest_id, tracked },
  });
}

// H4 parity: the 放棄 pointer sits behind the same explicit two-step
// confirmation the counter path required. One armed row at a time; the bar
// renders inside its own row and dispatches only through the counter-side
// descriptor's exact action.
const confirmAbandonId = ref(null);

const confirmRow = computed(() => {
  if (!confirmAbandonId.value) return null;
  return counterRowFor(confirmAbandonId.value);
});

function confirmAbandonNow() {
  const row = confirmRow.value;
  if (!row || !row.abandon || !row.abandon.enabled) return;
  emit("quest_abandon", {
    action_id: row.abandon.action_id,
    payload: { quest_id: row.quest_id },
  });
  confirmAbandonId.value = null;
}
</script>

<template>
  <section class="quest-log" data-testid="quest-log">
    <h3 class="quest-log__title" data-testid="quest-log__title">我的任務簿</h3>

    <p
      v-if="unavailable"
      class="quest-log__unavailable"
      data-testid="quest-log__unavailable"
      :data-reason-code="questLog.reason?.code"
    >
      {{ questLog.reason?.message }}
    </p>

    <p v-else-if="absent" class="quest-log__absent" data-testid="quest-log__absent">
      尚未取得任務簿資料
    </p>

    <p v-else-if="rows.length === 0" class="quest-log__empty" data-testid="quest-log__empty">
      目前沒有任何任務紀錄。
    </p>

    <template v-else>
      <section
        v-for="group in groups"
        :key="group.key"
        class="quest-log__section"
        :aria-label="group.label"
      >
        <h4 class="quest-log__section-title" :data-testid="`quest-log__group--${group.key}`">
          {{ group.label }}
        </h4>

        <div
          v-for="row in group.rows"
          :key="row.quest_id"
          class="quest-log__row"
          :data-testid="`quest-log__row--${row.quest_id}`"
        >
          <div class="quest-log__row-head">
            <span class="quest-log__row-name">{{ row.display_name }}</span>
            <span class="quest-log__state" data-testid="quest-log__quest-state">
              {{ group.label }}
            </span>
          </div>

          <p class="quest-log__issuer" data-testid="quest-log__issuer">
            <span class="quest-log__issuer-kind">{{ issuerKindLabel(row.issuer?.kind) }}</span>
            {{ row.issuer?.label }}
            <span
              v-if="settlementLabel(row.settlement)"
              class="quest-log__settlement"
              data-testid="quest-log__settlement"
            >（{{ settlementLabel(row.settlement) }}）</span>
          </p>

          <p class="quest-log__row-objective">{{ row.objective_line }}</p>
          <p class="quest-log__stage" data-testid="quest-log__quest-stage">
            第 {{ row.stage_index }} 階段 · 進度 {{ row.stage_progress }}
          </p>
          <p
            v-if="row.deadline_line"
            class="quest-log__deadline"
            data-testid="quest-log__quest-deadline"
          >
            {{ row.deadline_line }}
          </p>
          <p class="quest-log__detail" data-testid="quest-log__quest-detail">
            {{ row.detail }}
          </p>
          <p v-if="row.reward_line" class="quest-log__reward" data-testid="quest-log__reward">
            獎勵：{{ row.reward_line }}
          </p>

          <div class="quest-log__actions">
            <template v-if="row.state === 'in_progress'">
              <button
                v-if="!row.tracked"
                type="button"
                class="quest-log__action"
                data-testid="quest-log__track"
                @click="dispatchTrack(row, true)"
              >
                追蹤
              </button>
              <button
                v-else
                type="button"
                class="quest-log__action"
                data-testid="quest-log__untrack"
                @click="dispatchTrack(row, false)"
              >
                取消追蹤
              </button>
            </template>
            <template v-else>
              <button type="button" class="quest-log__action" data-testid="quest-log__track" disabled>
                追蹤
              </button>
              <span class="quest-log__reason" data-testid="quest-log__track-reason">
                （{{ TRACK_LOCKED_REASON }}）
              </span>
            </template>

            <!-- Counter-only actions: rendered strictly from the matched
                 guild.quests row, mirroring its descriptor byte-for-byte. -->
            <template v-if="counterRowFor(row.quest_id)">
              <button
                v-if="counterRowFor(row.quest_id).abandon && counterRowFor(row.quest_id).abandon.enabled"
                type="button"
                class="quest-log__action"
                data-testid="quest-log__abandon"
                @click="confirmAbandonId = row.quest_id"
              >
                {{ counterRowFor(row.quest_id).abandon.label }}
              </button>
              <span
                v-else-if="counterRowFor(row.quest_id).abandon && !counterRowFor(row.quest_id).abandon.enabled && counterRowFor(row.quest_id).abandon.disabled_reason"
                class="quest-log__reason"
                data-testid="quest-log__abandon-reason"
              >
                （{{ counterRowFor(row.quest_id).abandon.disabled_reason.message }}）
              </span>
              <button
                v-if="counterRowFor(row.quest_id).turnin && counterRowFor(row.quest_id).turnin.enabled"
                type="button"
                class="quest-log__action"
                data-testid="quest-log__turnin"
                @click="emit('quest_turnin', { action_id: counterRowFor(row.quest_id).turnin.action_id, payload: { quest_id: row.quest_id } })"
              >
                {{ counterRowFor(row.quest_id).turnin.label }}
              </button>
              <span
                v-else-if="counterRowFor(row.quest_id).turnin && !counterRowFor(row.quest_id).turnin.enabled && counterRowFor(row.quest_id).turnin.disabled_reason"
                class="quest-log__reason"
                data-testid="quest-log__turnin-reason"
              >
                （{{ counterRowFor(row.quest_id).turnin.disabled_reason.message }}）
              </span>
            </template>
          </div>

          <!-- The explicit two-step abandon confirmation: arm on 放棄, then
               only the labelled 確認放棄 dispatches guild.quest_abandon. -->
          <div
            v-if="confirmRow && confirmRow.quest_id === row.quest_id"
            class="quest-log__confirm"
            data-testid="quest-log__abandon-confirm"
          >
            <p class="quest-log__confirm-text" data-testid="quest-log__abandon-confirm-text">
              放棄「{{ row.display_name }}」後任務會失敗，且無法回復。
            </p>
            <div class="quest-log__confirm-actions">
              <button
                type="button"
                class="quest-log__action"
                data-testid="quest-log__abandon-confirm-yes"
                @click="confirmAbandonNow()"
              >
                確認放棄
              </button>
              <button
                type="button"
                class="quest-log__action"
                data-testid="quest-log__abandon-confirm-no"
                @click="confirmAbandonId = null"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.quest-log {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  box-sizing: border-box;
  padding: var(--sp-3) var(--sp-4);
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  font-family: var(--f-sans);
}

.quest-log__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.quest-log__absent,
.quest-log__unavailable,
.quest-log__empty {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: 0.85em;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.quest-log__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.quest-log__section-title {
  margin: 0;
  color: var(--seal-400);
  font-family: var(--f-display);
  font-size: 0.95em;
}

.quest-log__row {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2);
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-hi);
}

.quest-log__row-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-2);
}

.quest-log__row-name {
  color: var(--paper-50);
  font-family: var(--f-display);
}

.quest-log__state {
  color: var(--gold-400);
  font-family: var(--f-mono);
  font-size: 0.85em;
}

.quest-log__issuer {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.quest-log__issuer-kind {
  color: var(--gold-400);
  font-family: var(--f-mono);
}

.quest-log__settlement {
  color: var(--paper-500);
  font-family: var(--f-mono);
}

.quest-log__row-objective,
.quest-log__reward {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.quest-log__stage,
.quest-log__detail,
.quest-log__deadline {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.quest-log__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
}

.quest-log__action {
  padding: 2px var(--sp-2);
  color: var(--paper-50);
  background: transparent;
  border: 1px solid var(--seal-600);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: 0.85em;
  cursor: pointer;
}

.quest-log__action:hover {
  border-color: var(--seal-400);
  color: var(--seal-400);
}

.quest-log__action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  border-color: var(--ink-600);
  color: var(--paper-700);
}

.quest-log__reason {
  color: var(--warn);
  font-size: 0.85em;
  font-family: var(--f-mono);
}

.quest-log__confirm {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-2);
  border: 1px solid var(--seal-600);
  border-radius: var(--radius-sm);
  background: var(--panel-hi);
}

.quest-log__confirm-text {
  margin: 0;
  color: var(--paper-100);
  font-size: 0.85em;
  line-height: 1.5;
}

.quest-log__confirm-actions {
  display: flex;
  gap: var(--sp-2);
}
</style>
