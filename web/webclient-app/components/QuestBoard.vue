<script setup>
// QuestBoard (B4 services family): the guild quest surface of the `services`
// panel. Design D2: the surface is a host, not a data source — it renders
// only the committed `services` v1 payload (guild section: registration,
// quest board (接取), active quest records (回報·放棄·詳情), rank) and
// invents nothing. A missing guild section renders an honest absent marker.
import { computed, ref } from "vue";

const props = defineProps({
  // The committed `services` v1 panel payload.
  services: { type: Object, required: true },
});

const emit = defineEmits([
  "quest_accept",
  "quest_abandon",
  "quest_turnin",
  "exam_start",
  "quest_register",
  "open_lore",
]);

// The registry-owned unavailable form carries only `reason` — the guild
// section is absent, so no invented board/quest/rank content.
const unavailable = computed(() => props.services?.available === false);
const guild = computed(() => (unavailable.value ? null : (props.services?.guild ?? null)));
const registration = computed(() => guild.value?.registration ?? null);
const boardRows = computed(() => guild.value?.board ?? []);
const questRows = computed(() => guild.value?.quests ?? []);
const rank = computed(() => guild.value?.rank ?? null);

// Quest state labels mirror the server's bounded quest states
// (presentation/services.py QUEST_STATES): rendered as text, not color-only.
const QUEST_STATES = {
  in_progress: "進行中",
  completed: "已完成",
  failed: "失敗",
};

function questStateLabel(state) {
  return QUEST_STATES[state] ?? state;
}

// The promotion line renders next_rank / next_threshold only when the
// payload carries both (nullable pair per the bounded schema); a terminal
// rank (both null) degrades instead of printing a fabricated "null".
const hasNextStep = computed(
  () => rank.value?.next_rank != null && rank.value?.next_threshold != null,
);

// H4 (task 7.2): the 放棄 (abandon) pointer is placed behind the same
// explicit two-step confirmation the dock path (service_menu.js confirmMenu)
// already requires. The abandon button arms a local confirmation; only the
// explicit confirm dispatches the exact `guild.quest_abandon` action.
const confirmAbandon = ref(null);

function confirmAbandonNow() {
  const quest = confirmAbandon.value;
  if (!quest || !quest.abandon || !quest.abandon.enabled) return;
  emit("quest_abandon", {
    action_id: quest.abandon.action_id,
    payload: { quest_id: quest.quest_id },
  });
  confirmAbandon.value = null;
}
</script>

<template>
  <section class="quest-board" data-testid="quest-board">
    <h3 class="quest-board__title" data-testid="quest-board__title">公會任務板</h3>

    <!-- H4 (task 5.5): the single labelled control that opens the lore
         (圖鑑) drawer from the quest drawer. -->
    <button
      type="button"
      class="quest-board__action"
      data-testid="quest-board__open-lore"
      @click="emit('open_lore')"
    >
      世界圖鑑
    </button>

    <p
      v-if="unavailable"
      class="quest-board__unavailable"
      data-testid="quest-board__unavailable"
      :data-reason-code="services.reason?.code"
    >
      {{ services.reason?.message }}
    </p>

    <p v-else-if="!guild" class="quest-board__absent" data-testid="quest-board__absent">
      尚未取得公會資料
    </p>

    <template v-if="guild">
      <p
        v-if="registration"
        class="quest-board__registration"
        data-testid="quest-board__registration"
        :data-registered="String(registration.registered)"
      >
        <span class="quest-board__registration-state">
          {{ registration.registered ? "已加入公會" : "未加入公會" }}
        </span>
          <button
            v-if="registration.register && registration.register.enabled"
            type="button"
            class="quest-board__action"
            data-testid="quest-board__register"
            @click="emit('quest_register', { action_id: registration.register.action_id })"
          >
            {{ registration.register.label }}
          </button>
        <span
          v-if="registration.register && !registration.register.enabled && registration.register.disabled_reason"
          class="quest-board__reason"
          data-testid="quest-board__register-reason"
        >
          （{{ registration.register.disabled_reason.message }}）
        </span>
      </p>

      <section class="quest-board__section" aria-label="任務板">
        <h4 class="quest-board__section-title">任務板 — 接取</h4>
        <div
          v-for="row in boardRows"
          :key="row.definition_key"
          class="quest-board__row"
          :data-testid="`quest-board__board-row--${row.definition_key}`"
        >
          <div class="quest-board__row-head">
            <span class="quest-board__row-name">{{ row.display_name }}</span>
            <span class="quest-board__row-rank">等級 {{ row.rank }}</span>
          </div>
          <p class="quest-board__row-objective">{{ row.objective_summary }}</p>
          <p class="quest-board__row-reward">獎勵：{{ row.reward_summary }}</p>
          <button
            v-if="row.accept && row.accept.enabled"
            type="button"
            class="quest-board__action"
               @click="emit('quest_accept', { action_id: row.accept.action_id, payload: { definition_key: row.definition_key } })"
          >
            {{ row.accept.label }}
          </button>
          <span
            v-if="row.accept && !row.accept.enabled && row.accept.disabled_reason"
            class="quest-board__reason"
            data-testid="quest-board__accept-reason"
          >
            （{{ row.accept.disabled_reason.message }}）
          </span>
        </div>
      </section>

      <section class="quest-board__section" aria-label="任務紀錄">
        <h4 class="quest-board__section-title">任務紀錄 — 回報 · 放棄 · 詳情</h4>
        <div
          v-for="quest in questRows"
          :key="quest.quest_id"
          class="quest-board__row"
          :data-testid="`quest-board__quest-row--${quest.quest_id}`"
        >
          <div class="quest-board__row-head">
            <span class="quest-board__row-name">{{ quest.display_name }}</span>
            <span class="quest-board__state" data-testid="quest-board__quest-state">
              {{ questStateLabel(quest.state) }}
            </span>
          </div>
          <p class="quest-board__row-objective">{{ quest.objective_summary }}</p>
          <p class="quest-board__stage" data-testid="quest-board__quest-stage">
            第 {{ quest.stage_index }} 階段 · 進度 {{ quest.stage_progress }}
          </p>
          <p
            v-if="quest.deadline_line"
            class="quest-board__deadline"
            data-testid="quest-board__quest-deadline"
          >
            {{ quest.deadline_line }}
          </p>
          <p class="quest-board__detail" data-testid="quest-board__quest-detail">
            {{ quest.detail }}
          </p>
           <button
             v-if="quest.abandon && quest.abandon.enabled"
             type="button"
             class="quest-board__action"
             data-testid="quest-board__abandon"
             @click="confirmAbandon = quest"
           >
             {{ quest.abandon.label }}
           </button>
          <span
            v-if="quest.abandon && !quest.abandon.enabled && quest.abandon.disabled_reason"
            class="quest-board__reason"
            data-testid="quest-board__abandon-reason"
          >
            （{{ quest.abandon.disabled_reason.message }}）
          </span>
          <button
            v-if="quest.turnin && quest.turnin.enabled"
            type="button"
            class="quest-board__action"
             @click="emit('quest_turnin', { action_id: quest.turnin.action_id, payload: { quest_id: quest.quest_id } })"
          >
            {{ quest.turnin.label }}
          </button>
          <span
            v-if="quest.turnin && !quest.turnin.enabled && quest.turnin.disabled_reason"
            class="quest-board__reason"
            data-testid="quest-board__turnin-reason"
          >
            （{{ quest.turnin.disabled_reason.message }}）
          </span>
        </div>
      </section>

      <section
        v-if="rank"
        class="quest-board__section"
        data-testid="quest-board__rankblock"
        aria-label="公會等級"
      >
        <h4 class="quest-board__section-title">公會等級</h4>
        <p class="quest-board__rank" data-testid="quest-board__rank">
          等級 {{ rank.rank }}
        </p>
          <p class="quest-board__merit" data-testid="quest-board__merit">
            <template v-if="hasNextStep">
              功績 {{ rank.merit }} · 升格至 {{ rank.next_rank }} 需 {{ rank.next_threshold }}
            </template>
            <template v-else>
              功績 {{ rank.merit }}（最高等級）
            </template>
          </p>
        <button
          v-if="rank.eligible"
          type="button"
          class="quest-board__action"
          data-testid="quest-board__exam"
          @click="emit('exam_start', { action_id: rank.exam_start?.action_id })"
        >
          {{ rank.exam_start?.label }}
        </button>
        <span
          v-if="!rank.eligible && rank.exam_start && rank.exam_start.disabled_reason"
          class="quest-board__reason"
          data-testid="quest-board__exam-reason"
        >
           （{{ rank.exam_start.disabled_reason.message }}）
         </span>
       </section>

       <!-- The explicit two-step confirmation for the abandon pointer (task
            7.2): arm on the 放棄 button, then only the labelled 確認放棄
            dispatches the exact guild.quest_abandon. -->
       <div
         v-if="confirmAbandon"
         class="quest-board__confirm"
         data-testid="quest-board__abandon-confirm"
       >
         <p class="quest-board__confirm-text" data-testid="quest-board__abandon-confirm-text">
           放棄「{{ confirmAbandon.display_name }}」後任務會失敗，且無法回復。
         </p>
         <div class="quest-board__confirm-actions">
           <button
             type="button"
             class="quest-board__action"
             data-testid="quest-board__abandon-confirm-yes"
             @click="confirmAbandonNow()"
           >
             確認放棄
           </button>
           <button
             type="button"
             class="quest-board__action"
             data-testid="quest-board__abandon-confirm-no"
             @click="confirmAbandon = null"
           >
             取消
           </button>
         </div>
       </div>
    </template>
  </section>
</template>

<style scoped>
.quest-board {
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

.quest-board__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.quest-board__absent,
.quest-board__unavailable {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: 0.85em;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.quest-board__registration {
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--paper-300);
  font-size: 0.85em;
}

.quest-board__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.quest-board__section-title {
  margin: 0;
  color: var(--seal-400);
  font-family: var(--f-display);
  font-size: 0.95em;
}

.quest-board__row {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2);
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-hi);
}

.quest-board__row-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-2);
}

.quest-board__row-name {
  color: var(--paper-50);
  font-family: var(--f-display);
}

.quest-board__row-rank {
  color: var(--gold-400);
  font-family: var(--f-mono);
  font-size: 0.85em;
}

.quest-board__row-objective,
.quest-board__row-reward {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.quest-board__action {
  align-self: flex-start;
  padding: 2px var(--sp-2);
  color: var(--paper-50);
  background: transparent;
  border: 1px solid var(--seal-600);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: 0.85em;
  cursor: pointer;
}

.quest-board__action:hover {
  border-color: var(--seal-400);
  color: var(--seal-400);
}

.quest-board__reason {
  color: var(--warn);
  font-size: 0.85em;
  font-family: var(--f-mono);
}

.quest-board__state {
  color: var(--gold-400);
  font-family: var(--f-mono);
  font-size: 0.85em;
}

.quest-board__stage,
.quest-board__detail,
.quest-board__deadline {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.quest-board__rank {
  margin: 0;
  color: var(--paper-50);
  font-size: 0.85em;
}

.quest-board__merit {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.quest-board__confirm {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-2);
  border: 1px solid var(--seal-600);
  border-radius: var(--radius-sm);
  background: var(--panel-hi);
}

.quest-board__confirm-text {
  margin: 0;
  color: var(--paper-100);
  font-size: 0.85em;
  line-height: 1.5;
}

.quest-board__confirm-actions {
  display: flex;
  gap: var(--sp-2);
}
</style>
